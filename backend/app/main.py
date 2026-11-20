import os
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from backend.app.database import Base, DATABASE_URL, SessionLocal, engine, get_db
from backend.app.models import (
    AdminUser,
    BattingEntry,
    BowlingEntry,
    Commentary,
    Innings,
    Match,
    Player,
    PlayerTeamMembership,
    Series,
    SeriesTeamMembership,
    Team,
)
from backend.app.schemas import (
    LoginInput,
    MatchInput,
    MatchOut,
    PlayerInput,
    PlayerOut,
    SeriesInput,
    SeriesOut,
    TeamInput,
    TeamOut,
)
from backend.app.security import hash_password, verify_password

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
    bootstrap_admin()
    yield


app = FastAPI(title="Cricket Hub API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[APP_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


def session_cookie_policy() -> tuple[bool, str]:
    secure = os.getenv("APP_ENV", "development").lower() == "production"
    return secure, "none" if secure else "strict"


def bootstrap_admin() -> None:
    email = os.getenv("CRICKET_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("CRICKET_ADMIN_PASSWORD", "")
    if "@" not in email or len(email) > 254:
        raise RuntimeError("Set CRICKET_ADMIN_EMAIL to a valid admin email before starting the API")
    if len(password) < 12:
        raise RuntimeError("Set CRICKET_ADMIN_PASSWORD to a password with at least 12 characters")

    with SessionLocal() as db:
        admins = db.scalars(select(AdminUser).order_by(AdminUser.id)).all()
        if not admins:
            db.add(AdminUser(email=email, password_hash=hash_password(password)))
        else:
            admin = next((existing for existing in admins if existing.email == email), admins[0])
            admin.email = email
            if not verify_password(password, admin.password_hash):
                admin.password_hash = hash_password(password)
        db.commit()


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


def player_name_snapshot(db: Session, player_id: str | None, fallback: str) -> str:
    if player_id is None:
        return fallback
    player = db.get(Player, player_id)
    if player is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selected player does not exist",
        )
    return player.display_name or player.full_name


def apply_match_input(match: Match, data: MatchInput, db: Session) -> None:
    old_team_ids = (match.team1_id, match.team2_id)
    old_team_codes = (match.team1_code, match.team2_code)
    old_innings_team_codes = {
        innings.innings_number: innings.team_code for innings in match.innings
    }
    existing_batting = {
        (innings.innings_number, entry.position): entry
        for innings in match.innings
        for entry in innings.batting
    }
    existing_bowling = {
        (innings.innings_number, entry.position): entry
        for innings in match.innings
        for entry in innings.bowling
    }
    old_snapshots = {
        "series_id": match.series,
        "team1_id": (match.team1, match.team1_code),
        "team2_id": (match.team2, match.team2_code),
    }

    def resolve(field_name: str, model, requested_id: str | None, existing_id: str | None, old_snapshot, new_snapshot, label: str):
        if (
            existing_id
            and new_snapshot == old_snapshot
            and (field_name not in data.model_fields_set or requested_id == existing_id)
        ):
            return existing_id, db.get(model, existing_id), True
        if field_name in data.model_fields_set:
            if requested_id is None:
                return None, None, False
            return requested_id, require_active_master(db, model, requested_id, label), False
        return None, None, False

    match.series_id, series_master, keep_series_snapshot = resolve(
        "series_id", Series, data.series_id, match.series_id, old_snapshots["series_id"], data.series, "series"
    )
    match.team1_id, team1_master, keep_team1_snapshot = resolve(
        "team1_id",
        Team,
        data.team1_id,
        match.team1_id,
        old_snapshots["team1_id"],
        (data.team1, data.team1_code),
        "team",
    )
    match.team2_id, team2_master, keep_team2_snapshot = resolve(
        "team2_id",
        Team,
        data.team2_id,
        match.team2_id,
        old_snapshots["team2_id"],
        (data.team2, data.team2_code),
        "team",
    )

    if match.team1_id and match.team1_id == match.team2_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A match must use two different registered teams",
        )

    if match.series_id and not (
        keep_series_snapshot and keep_team1_snapshot and keep_team2_snapshot
    ):
        participant_ids = set(
            db.scalars(
                select(SeriesTeamMembership.team_id).where(
                    SeriesTeamMembership.series_id == match.series_id,
                    SeriesTeamMembership.is_active.is_(True),
                )
            ).all()
        )
        selected_ids = {team_id for team_id in (match.team1_id, match.team2_id) if team_id}
        if participant_ids and not selected_ids.issubset(participant_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Both registered teams must participate in the selected series",
            )

    for innings_index, innings in enumerate(data.innings, start=1):
        innings_team_id = (
            match.team1_id if innings.team_code == data.team1_code else match.team2_id
        )
        for position, entry in enumerate(innings.batting, start=1):
            if entry.player_id is None:
                continue
            if innings_team_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="A registered scorecard player requires a registered match team",
                )
            old_entry = existing_batting.get((innings_index, position))
            old_team_id = (
                old_team_ids[0] if old_innings_team_codes.get(innings_index) == old_team_codes[0]
                else old_team_ids[1]
            )
            keep_existing_player = (
                old_entry is not None
                and old_entry.player_id == entry.player_id
                and old_innings_team_codes.get(innings_index) == innings.team_code
                and old_team_id == innings_team_id
            )
            player = db.get(Player, entry.player_id) if keep_existing_player else require_active_master(
                db, Player, entry.player_id, "player"
            )
            if player is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Selected player does not exist",
                )
            if keep_existing_player:
                continue
            membership_id = db.scalar(
                select(PlayerTeamMembership.id).where(
                    PlayerTeamMembership.player_id == player.id,
                    PlayerTeamMembership.team_id == innings_team_id,
                    PlayerTeamMembership.is_active.is_(True),
                )
            )
            if membership_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="The selected player is not associated with this innings team",
                )
        for position, entry in enumerate(innings.bowling, start=1):
            if entry.player_id is None:
                continue
            if innings_team_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="A registered scorecard player requires a registered match team",
                )
            old_entry = existing_bowling.get((innings_index, position))
            old_team_id = (
                old_team_ids[0] if old_innings_team_codes.get(innings_index) == old_team_codes[0]
                else old_team_ids[1]
            )
            keep_existing_player = (
                old_entry is not None
                and old_entry.player_id == entry.player_id
                and old_innings_team_codes.get(innings_index) == innings.team_code
                and old_team_id == innings_team_id
            )
            player = db.get(Player, entry.player_id) if keep_existing_player else require_active_master(
                db, Player, entry.player_id, "player"
            )
            if player is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Selected player does not exist",
                )
            if keep_existing_player:
                continue
            membership_id = db.scalar(
                select(PlayerTeamMembership.id).where(
                    PlayerTeamMembership.player_id == player.id,
                    PlayerTeamMembership.team_id == innings_team_id,
                    PlayerTeamMembership.is_active.is_(True),
                )
            )
            if membership_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="The selected player is not associated with this innings team",
                )

    match.series = data.series if keep_series_snapshot else (series_master.name if series_master else data.series)
    match.stage = data.stage
    match.status = data.status
    match.team1 = data.team1 if keep_team1_snapshot else (team1_master.name if team1_master else data.team1)
    match.team1_code = data.team1_code if keep_team1_snapshot else (team1_master.short_name if team1_master else data.team1_code)
    match.team2 = data.team2 if keep_team2_snapshot else (team2_master.name if team2_master else data.team2)
    match.team2_code = data.team2_code if keep_team2_snapshot else (team2_master.short_name if team2_master else data.team2_code)
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
                BattingEntry(
                    position=position,
                    player=(
                        existing_batting[(index, position)].player
                        if entry.player_id is not None
                        and (index, position) in existing_batting
                        and existing_batting[(index, position)].player_id == entry.player_id
                        else player_name_snapshot(db, entry.player_id, entry.player)
                    ),
                    player_id=entry.player_id,
                    dismissal=entry.dismissal,
                    runs=entry.runs,
                    balls=entry.balls,
                    fours=entry.fours,
                    sixes=entry.sixes,
                )
                for position, entry in enumerate(innings.batting, start=1)
            ],
            bowling=[
                BowlingEntry(
                    position=position,
                    player=(
                        existing_bowling[(index, position)].player
                        if entry.player_id is not None
                        and (index, position) in existing_bowling
                        and existing_bowling[(index, position)].player_id == entry.player_id
                        else player_name_snapshot(db, entry.player_id, entry.player)
                    ),
                    player_id=entry.player_id,
                    overs=entry.overs,
                    maidens=entry.maidens,
                    runs=entry.runs,
                    wickets=entry.wickets,
                )
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


def commit_master_data(db: Session, conflict_message: str) -> None:
    try:
        db.commit()
    except IntegrityError as cause:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=conflict_message) from cause


def validate_active_teams(
    db: Session,
    team_ids: list[str],
    existing_team_ids: set[str] | None = None,
) -> None:
    if not team_ids:
        return
    active_ids = set(db.scalars(
        select(Team.id).where(Team.id.in_(team_ids), Team.is_active.is_(True))
    ).all())
    allowed_existing_ids = existing_team_ids or set()
    if not set(team_ids).issubset(active_ids | allowed_existing_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="One or more teams are missing or inactive",
        )


def sync_player_team_memberships(db: Session, player_id: str, team_ids: list[str]) -> None:
    memberships = db.scalars(
        select(PlayerTeamMembership).where(PlayerTeamMembership.player_id == player_id)
    ).all()
    active_ids = {membership.team_id for membership in memberships if membership.is_active}
    selected_ids = set(team_ids)
    for membership in memberships:
        if membership.is_active and membership.team_id not in selected_ids:
            membership.is_active = False
            membership.end_date = date.today()
    for team_id in selected_ids - active_ids:
        db.add(
            PlayerTeamMembership(
                player_id=player_id,
                team_id=team_id,
                start_date=date.today(),
                is_active=True,
            )
        )


def sync_series_team_memberships(db: Session, series_id: str, team_ids: list[str]) -> None:
    memberships = db.scalars(
        select(SeriesTeamMembership).where(SeriesTeamMembership.series_id == series_id)
    ).all()
    active_ids = {membership.team_id for membership in memberships if membership.is_active}
    selected_ids = set(team_ids)
    for membership in memberships:
        if membership.is_active and membership.team_id not in selected_ids:
            membership.is_active = False
    for team_id in selected_ids - active_ids:
        db.add(SeriesTeamMembership(series_id=series_id, team_id=team_id, is_active=True))


def require_active_master(db: Session, model, identifier: str, label: str):
    record = db.get(model, identifier)
    if record is None or not record.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Selected {label} does not exist or is inactive",
        )
    return record


@app.get("/api/v1/admin/teams", response_model=list[TeamOut])
def admin_list_teams(
    q: str | None = Query(default=None, max_length=100),
    active_only: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    statement = select(Team).order_by(func.lower(Team.name), Team.id)
    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.where(or_(Team.name.ilike(pattern), Team.short_name.ilike(pattern)))
    if active_only is not None:
        statement = statement.where(Team.is_active.is_(active_only))
    return db.scalars(statement.limit(limit).offset(offset)).all()


@app.post("/api/v1/admin/teams", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
def admin_create_team(
    payload: TeamInput,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    team = Team(**payload.model_dump())
    db.add(team)
    commit_master_data(db, "A team with this name or short name already exists")
    db.refresh(team)
    return team


@app.put("/api/v1/admin/teams/{team_id}", response_model=TeamOut)
def admin_update_team(
    team_id: str,
    payload: TeamInput,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    for field, value in payload.model_dump().items():
        setattr(team, field, value)
    commit_master_data(db, "A team with this name or short name already exists")
    db.refresh(team)
    return team


@app.get("/api/v1/admin/players", response_model=list[PlayerOut])
def admin_list_players(
    q: str | None = Query(default=None, max_length=120),
    team_id: str | None = None,
    active_only: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    statement = select(Player).options(selectinload(Player.team_memberships)).order_by(
        func.lower(Player.full_name), Player.id
    )
    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.where(
            or_(Player.full_name.ilike(pattern), Player.display_name.ilike(pattern))
        )
    if active_only is not None:
        statement = statement.where(Player.is_active.is_(active_only))
    if team_id:
        statement = statement.join(PlayerTeamMembership).where(
            PlayerTeamMembership.team_id == team_id,
            PlayerTeamMembership.is_active.is_(True),
            Player.is_active.is_(True),
        )
    return db.scalars(statement.limit(limit).offset(offset)).unique().all()


@app.post("/api/v1/admin/players", response_model=PlayerOut, status_code=status.HTTP_201_CREATED)
def admin_create_player(
    payload: PlayerInput,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    validate_active_teams(db, payload.team_ids)
    player = Player(**payload.model_dump(exclude={"team_ids"}))
    db.add(player)
    db.flush()
    sync_player_team_memberships(db, player.id, payload.team_ids)
    commit_master_data(db, "Could not save player and team memberships")
    db.refresh(player)
    return player


@app.put("/api/v1/admin/players/{player_id}", response_model=PlayerOut)
def admin_update_player(
    player_id: str,
    payload: PlayerInput,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    player = db.get(Player, player_id)
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    team_ids = payload.team_ids if "team_ids" in payload.model_fields_set else player.team_ids
    validate_active_teams(db, team_ids, set(player.team_ids))
    for field, value in payload.model_dump(exclude={"team_ids"}).items():
        setattr(player, field, value)
    sync_player_team_memberships(db, player.id, team_ids)
    commit_master_data(db, "Could not save player and team memberships")
    db.refresh(player)
    return player


@app.get("/api/v1/admin/series", response_model=list[SeriesOut])
def admin_list_series(
    q: str | None = Query(default=None, max_length=160),
    active_only: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    statement = select(Series).options(selectinload(Series.team_memberships)).order_by(
        func.lower(Series.name), Series.id
    )
    if q:
        statement = statement.where(Series.name.ilike(f"%{q.strip()}%"))
    if active_only is not None:
        statement = statement.where(Series.is_active.is_(active_only))
    return db.scalars(statement.limit(limit).offset(offset)).unique().all()


@app.post("/api/v1/admin/series", response_model=SeriesOut, status_code=status.HTTP_201_CREATED)
def admin_create_series(
    payload: SeriesInput,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    validate_active_teams(db, payload.team_ids)
    series = Series(**payload.model_dump(exclude={"team_ids"}))
    db.add(series)
    db.flush()
    sync_series_team_memberships(db, series.id, payload.team_ids)
    commit_master_data(db, "A series with this name already exists")
    db.refresh(series)
    return series


@app.put("/api/v1/admin/series/{series_id}", response_model=SeriesOut)
def admin_update_series(
    series_id: str,
    payload: SeriesInput,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    series = db.get(Series, series_id)
    if series is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")
    team_ids = payload.team_ids if "team_ids" in payload.model_fields_set else series.team_ids
    validate_active_teams(db, team_ids, set(series.team_ids))
    for field, value in payload.model_dump(exclude={"team_ids"}).items():
        setattr(series, field, value)
    sync_series_team_memberships(db, series.id, team_ids)
    commit_master_data(db, "A series with this name already exists")
    db.refresh(series)
    return series


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
        return {"authenticated": False}
    return {"authenticated": True}


@app.post("/api/v1/auth/login")
def login(payload: LoginInput, request: Request, response: Response, db: Session = Depends(get_db)):
    validate_origin(request)
    admin = db.scalar(select(AdminUser).where(AdminUser.email == payload.email.strip().lower()))
    if admin is None or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email or password is incorrect")
    token = secrets.token_urlsafe(32)
    sessions[token] = time.time() + SESSION_SECONDS
    secure_cookie, same_site = session_cookie_policy()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=secure_cookie,
        samesite=same_site,
        path="/",
    )
    return {"authenticated": True}


@app.post("/api/v1/auth/logout")
def logout(request: Request, response: Response):
    validate_origin(request)
    sessions.pop(request.cookies.get(SESSION_COOKIE, ""), None)
    secure_cookie, same_site = session_cookie_policy()
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=secure_cookie,
        samesite=same_site,
    )
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
    apply_match_input(match, payload, db)
    db.add(match)
    db.commit()
    return serialize_match(load_match(db, match.id))


@app.put("/api/v1/matches/{match_id}", response_model=MatchOut)
def update_match(match_id: str, payload: MatchInput, _: None = Depends(require_admin), db: Session = Depends(get_db)):
    match = load_match(db, match_id)
    apply_match_input(match, payload, db)
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
