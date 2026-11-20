import os
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from backend.app.database import Base, DATABASE_URL, engine, get_db
from backend.app.models import BattingEntry, BowlingEntry, Commentary, Innings, Match
from backend.app.schemas import LoginInput, MatchInput, MatchOut

APP_ORIGIN = os.getenv("CRICKET_APP_ORIGIN", "http://127.0.0.1:5173")
SESSION_COOKIE = "cricket_admin_session"
SESSION_SECONDS = 8 * 60 * 60
sessions: dict[str, float] = {}
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    if DATABASE_URL.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Cricket Hub API", version="1.0.0", lifespan=lifespan)


def validate_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin != APP_ORIGIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-origin request rejected")


def require_admin(request: Request) -> None:
    validate_origin(request)
    token = request.cookies.get(SESSION_COOKIE)
    expires_at = sessions.get(token or "")
    if expires_at is None or expires_at <= time.time():
        sessions.pop(token or "", None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin sign-in required")


def load_match(db: Session, match_id: str) -> Match:
    statement = (
        select(Match)
        .where(Match.id == match_id)
        .options(
            selectinload(Match.innings).selectinload(Innings.batting),
            selectinload(Match.innings).selectinload(Innings.bowling),
            selectinload(Match.commentary),
        )
    )
    match = db.scalar(statement)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return match


def apply_match_input(match: Match, data: MatchInput) -> None:
    match.series = data.series
    match.stage = data.stage
    match.status = data.status
    match.team1 = data.team1
    match.team1_code = data.team1_code
    match.team2 = data.team2
    match.team2_code = data.team2_code
    match.date = data.date
    match.time = data.time
    match.venue = data.venue
    match.format = data.format
    match.result = data.result
    match.toss = data.toss
    match.innings = [
        Innings(
            innings_number=index,
            team_code=innings.team_code,
            total=innings.total,
            overs=innings.overs,
            batting=[
                BattingEntry(position=position, **entry.model_dump())
                for position, entry in enumerate(innings.batting, start=1)
            ],
            bowling=[
                BowlingEntry(position=position, **entry.model_dump())
                for position, entry in enumerate(innings.bowling, start=1)
            ],
        )
        for index, innings in enumerate(data.innings, start=1)
    ]
    match.commentary = [
        Commentary(position=position, text=line)
        for position, line in enumerate(data.commentary, start=1)
    ]


def serialize_match(match: Match) -> dict:
    return MatchOut.model_validate(match).model_dump(mode="json", by_alias=True)


@app.get("/api/v1/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.get("/api/v1/auth/session")
def auth_session(request: Request):
    token = request.cookies.get(SESSION_COOKIE, "")
    expires_at = sessions.get(token)
    if expires_at is None or expires_at <= time.time():
        sessions.pop(token, None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in")
    return {"authenticated": True}


@app.post("/api/v1/auth/login")
def login(payload: LoginInput, request: Request, response: Response):
    validate_origin(request)
    admin_email = os.getenv("CRICKET_ADMIN_EMAIL", "")
    admin_password = os.getenv("CRICKET_ADMIN_PASSWORD", "")
    if not admin_email or not admin_password:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin credentials are not configured on the server")
    valid_email = secrets.compare_digest(payload.email, admin_email)
    valid_password = secrets.compare_digest(payload.password, admin_password)
    if not (valid_email & valid_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email or password is incorrect")
    token = secrets.token_urlsafe(32)
    sessions[token] = time.time() + SESSION_SECONDS
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=os.getenv("APP_ENV", "development").lower() == "production",
        samesite="strict",
        path="/",
    )
    return {"authenticated": True}


@app.post("/api/v1/auth/logout")
def logout(request: Request, response: Response):
    validate_origin(request)
    sessions.pop(request.cookies.get(SESSION_COOKIE, ""), None)
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="strict")
    return {"authenticated": False}


@app.get("/api/v1/matches", response_model=list[MatchOut])
def list_matches(db: Session = Depends(get_db)):
    statement = (
        select(Match)
        .options(
            selectinload(Match.innings).selectinload(Innings.batting),
            selectinload(Match.innings).selectinload(Innings.bowling),
            selectinload(Match.commentary),
        )
        .order_by(Match.date.desc(), Match.id)
    )
    return [serialize_match(match) for match in db.scalars(statement).unique().all()]


@app.get("/api/v1/matches/{match_id}", response_model=MatchOut)
def get_match(match_id: str, db: Session = Depends(get_db)):
    return serialize_match(load_match(db, match_id))


@app.post("/api/v1/matches", response_model=MatchOut, status_code=status.HTTP_201_CREATED)
def create_match(payload: MatchInput, _: None = Depends(require_admin), db: Session = Depends(get_db)):
    match = Match(id=str(uuid.uuid4()))
    apply_match_input(match, payload)
    db.add(match)
    db.commit()
    return serialize_match(load_match(db, match.id))


@app.put("/api/v1/matches/{match_id}", response_model=MatchOut)
def update_match(match_id: str, payload: MatchInput, _: None = Depends(require_admin), db: Session = Depends(get_db)):
    match = load_match(db, match_id)
    apply_match_input(match, payload)
    db.commit()
    return serialize_match(load_match(db, match_id))


@app.delete("/api/v1/matches/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_match(match_id: str, _: None = Depends(require_admin), db: Session = Depends(get_db)):
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    db.delete(match)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
