from sqlalchemy import select

from backend.app.database import SessionLocal, normalize_database_url
from backend.app.models import AdminUser, PlayerTeamMembership
from backend.app.security import verify_password


def test_postgres_urls_use_installed_psycopg_driver():
    for scheme in ("postgres://", "postgresql://"):
        normalized = normalize_database_url(f"{scheme}user:password@localhost/cricket_hub")
        assert normalized.startswith("postgresql+psycopg://")


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


def test_cors_allows_configured_local_frontend_with_credentials(client):
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_production_session_cookie_is_cross_site_and_secure(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "test-only-password"},
    )
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "samesite=none" in cookie
    assert "secure" in cookie
    assert "httponly" in cookie


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


def test_master_data_crud_is_admin_protected_and_tracks_associations(client):
    assert client.get("/api/v1/admin/teams").status_code == 401
    assert client.get("/api/v1/admin/players").status_code == 401
    assert client.get("/api/v1/admin/series").status_code == 401
    assert client.post("/api/v1/admin/teams", json={}).status_code == 401
    sign_in(client)

    north = client.post(
        "/api/v1/admin/teams",
        json={"name": "North XI", "shortName": "NRTH", "country": "Testland", "category": "National"},
    )
    south = client.post(
        "/api/v1/admin/teams",
        json={"name": "South XI", "shortName": "STH", "isActive": True},
    )
    assert north.status_code == south.status_code == 201
    north_team = north.json()
    south_team = south.json()
    duplicate = client.post(
        "/api/v1/admin/teams",
        json={"name": "north xi", "shortName": "NORTH"},
    )
    assert duplicate.status_code == 409

    player_response = client.post(
        "/api/v1/admin/players",
        json={
            "fullName": "Alex Batter",
            "displayName": "A. Batter",
            "playingRole": "Batter",
            "battingStyle": "Right-hand bat",
            "teamIds": [north_team["id"], south_team["id"]],
        },
    )
    series_response = client.post(
        "/api/v1/admin/series",
        json={
            "name": "Test Championship",
            "category": "Tournament",
            "startDate": "2026-11-01",
            "endDate": "2026-11-30",
            "teamIds": [north_team["id"], south_team["id"]],
        },
    )
    assert player_response.status_code == series_response.status_code == 201
    assert set(player_response.json()["teamIds"]) == {north_team["id"], south_team["id"]}
    assert set(series_response.json()["teamIds"]) == {north_team["id"], south_team["id"]}

    deactivated_team = client.put(
        f"/api/v1/admin/teams/{north_team['id']}",
        json={"name": "North XI", "shortName": "NRTH", "isActive": False},
    )
    assert deactivated_team.status_code == 200
    unchanged_memberships = client.put(
        f"/api/v1/admin/players/{player_response.json()['id']}",
        json={"fullName": "Alex Batter", "playingRole": "Batter"},
    )
    assert unchanged_memberships.status_code == 200
    assert set(unchanged_memberships.json()["teamIds"]) == {north_team["id"], south_team["id"]}
    unchanged_series_teams = client.put(
        f"/api/v1/admin/series/{series_response.json()['id']}",
        json={"name": "Test Championship", "category": "Tournament"},
    )
    assert unchanged_series_teams.status_code == 200
    assert set(unchanged_series_teams.json()["teamIds"]) == {north_team["id"], south_team["id"]}

    updated_player = client.put(
        f"/api/v1/admin/players/{player_response.json()['id']}",
        json={
            "fullName": "Alex Batter",
            "displayName": "A. Batter",
            "playingRole": "Batter",
            "battingStyle": "Right-hand bat",
            "teamIds": [south_team["id"]],
        },
    )
    assert updated_player.status_code == 200
    assert updated_player.json()["teamIds"] == [south_team["id"]]
    with SessionLocal() as db:
        memberships = db.scalars(
            select(PlayerTeamMembership).where(
                PlayerTeamMembership.player_id == player_response.json()["id"]
            )
        ).all()
    assert {(membership.team_id, membership.is_active) for membership in memberships} == {
        (north_team["id"], False),
        (south_team["id"], True),
    }


def test_master_linked_match_preserves_historical_snapshots_after_deactivation(client):
    sign_in(client)
    north = client.post(
        "/api/v1/admin/teams",
        json={"name": "North XI", "shortName": "NRTH"},
    ).json()
    south = client.post(
        "/api/v1/admin/teams",
        json={"name": "South XI", "shortName": "STH"},
    ).json()
    player = client.post(
        "/api/v1/admin/players",
        json={
            "fullName": "Alex Batter",
            "displayName": "A. Batter",
            "playingRole": "Batter",
            "teamIds": [north["id"]],
        },
    ).json()
    series = client.post(
        "/api/v1/admin/series",
        json={"name": "Test Championship", "teamIds": [north["id"], south["id"]]},
    ).json()
    innings = [dict(item) for item in MATCH["innings"]]
    innings[0] = {
        **innings[0],
        "batting": [{**innings[0]["batting"][0], "playerId": player["id"]}],
    }
    payload = {
        **MATCH,
        "seriesId": series["id"],
        "team1Id": north["id"],
        "team2Id": south["id"],
        "innings": innings,
    }
    created = client.post("/api/v1/matches", json=payload)
    assert created.status_code == 201
    match = created.json()
    assert match["series"] == "Test Championship"
    assert match["team1"] == "North XI"
    assert match["innings"][0]["batting"][0]["player"] == "A. Batter"

    linked_payload = {
        **payload,
        "series": match["series"],
        "team1": match["team1"],
        "team1Code": match["team1Code"],
        "team2": match["team2"],
        "team2Code": match["team2Code"],
        "innings": match["innings"],
    }
    team_update = client.put(
        f"/api/v1/admin/teams/{north['id']}",
        json={"name": "Northern Club", "shortName": "NORTH", "isActive": False},
    )
    player_update = client.put(
        f"/api/v1/admin/players/{player['id']}",
        json={
            "fullName": "Alex Batter",
            "displayName": "Alex B.",
            "playingRole": "Batter",
            "isActive": False,
            "teamIds": [],
        },
    )
    series_update = client.put(
        f"/api/v1/admin/series/{series['id']}",
        json={"name": "Renamed Championship", "isActive": False, "teamIds": []},
    )
    assert team_update.status_code == player_update.status_code == series_update.status_code == 200

    changed = {**linked_payload, "venue": "Updated ground"}
    updated = client.put(f"/api/v1/matches/{match['id']}", json=changed)
    assert updated.status_code == 200
    result = updated.json()
    assert result["series"] == "Test Championship"
    assert result["team1"] == "North XI"
    assert result["team1Code"] == "NRTH"
    assert result["innings"][0]["batting"][0]["player"] == "A. Batter"
    assert result["venue"] == "Updated ground"
