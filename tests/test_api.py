from sqlalchemy import select

from backend.app.database import SessionLocal
from backend.app.models import AdminUser
from backend.app.security import verify_password


MATCH = {
    "series": "Test series",
    "stage": "Final",
    "status": "Completed",
    "team1": "North XI",
    "team1Code": "NRTH",
    "team2": "South XI",
    "team2Code": "STH",
    "date": "2026-11-20",
    "time": "10:00",
    "venue": "Test ground",
    "format": "Test",
    "result": "North XI won",
    "toss": "North XI elected to bat",
    "innings": [
        {
            "teamCode": "NRTH",
            "total": "200",
            "overs": "",
            "batting": [{"player": "Batter", "dismissal": "not out", "runs": 100, "balls": 120, "fours": 12, "sixes": 1}],
            "bowling": [{"player": "Bowler", "overs": "20", "maidens": 2, "runs": 55, "wickets": 3}],
        },
        {"teamCode": "STH", "total": "150", "overs": "", "batting": [], "bowling": []},
        {"teamCode": "NRTH", "total": "180", "overs": "", "batting": [], "bowling": []},
        {"teamCode": "STH", "total": "120", "overs": "", "batting": [], "bowling": []},
    ],
    "commentary": ["North XI won the toss and elected to bat.", "Batter reaches a century."],
}


def sign_in(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "test-only-password"},
    )
    assert response.status_code == 200
    assert response.json() == {"authenticated": True}


def test_health_checks_database(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_startup_seeds_one_hashed_admin_without_signup(client):
    with SessionLocal() as db:
        admins = db.scalars(select(AdminUser)).all()
    assert len(admins) == 1
    assert admins[0].email == "admin@example.test"
    assert admins[0].password_hash != "test-only-password"
    assert verify_password("test-only-password", admins[0].password_hash)
    assert client.post("/api/v1/auth/signup", json={}).status_code in (404, 405)
    assert client.get("/api/v1/auth/session").json() == {"authenticated": False}


def test_match_crud_persists_nested_scorecard_and_commentary(client):
    assert client.get("/api/v1/matches").json() == []
    assert client.post("/api/v1/matches", json=MATCH).status_code == 401
    sign_in(client)

    created = client.post("/api/v1/matches", json=MATCH)
    assert created.status_code == 201
    match = created.json()
    assert match["team1Code"] == "NRTH"
    assert len(match["innings"]) == 4
    assert match["innings"][0]["batting"][0]["runs"] == 100
    assert match["innings"][0]["bowling"][0]["wickets"] == 3
    assert match["commentary"] == MATCH["commentary"]

    changed = {**MATCH, "venue": "Updated ground"}
    updated = client.put(f"/api/v1/matches/{match['id']}", json=changed)
    assert updated.status_code == 200
    assert updated.json()["venue"] == "Updated ground"

    assert client.get(f"/api/v1/matches/{match['id']}").json()["innings"][3]["total"] == "120"
    assert client.delete(f"/api/v1/matches/{match['id']}").status_code == 204
    assert client.get("/api/v1/matches").json() == []


def test_login_validation_and_origin_protection(client):
    invalid_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "wrong"},
    )
    assert invalid_login.status_code == 401

    sign_in(client)
    rejected = client.post(
        "/api/v1/matches",
        json=MATCH,
        headers={"origin": "https://attacker.example"},
    )
    assert rejected.status_code == 403


def test_invalid_match_data_is_rejected(client):
    sign_in(client)
    invalid = {**MATCH, "status": "Live"}
    response = client.post("/api/v1/matches", json=invalid)
    assert response.status_code == 422

    invalid_team = {**MATCH, "team2Code": "NRTH"}
    response = client.post("/api/v1/matches", json=invalid_team)
    assert response.status_code == 422
