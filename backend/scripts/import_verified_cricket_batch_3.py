"""Load verified women's international white-ball fixtures (batch 3)."""

from datetime import date

from sqlalchemy import func, select

from backend.app.database import SessionLocal
from backend.app.models import Match, Series, SeriesTeamMembership, Team


TEAMS = (
    ("Australia Women", "AUSW", "Australia"), ("Bangladesh Women", "BANW", "Bangladesh"),
    ("India Women", "INDW", "India"), ("New Zealand Women", "NZW", "New Zealand"),
    ("South Africa Women", "SAW", "South Africa"), ("Sri Lanka Women", "SLW", "Sri Lanka"),
)
SERIES = (
    ("India Women tour of South Africa, 2026", "2026-12-09", "2026-12-30", ("South Africa Women", "India Women")),
    ("Bangladesh Women tour of New Zealand, 2026", "2026-12-10", "2026-12-23", ("New Zealand Women", "Bangladesh Women")),
    ("Australia Women tour of Sri Lanka, 2026", "2026-12-15", "2026-12-20", ("Sri Lanka Women", "Australia Women")),
)
FIXTURES = (
    ("Bangladesh Women tour of New Zealand, 2026", "1st T20I", "T20I", "New Zealand Women", "Bangladesh Women", "2026-12-10", "20:00 NZDT", "Saxton Oval, Nelson"),
    ("Bangladesh Women tour of New Zealand, 2026", "2nd T20I", "T20I", "New Zealand Women", "Bangladesh Women", "2026-12-12", "20:00 NZDT", "Saxton Oval, Nelson"),
    ("Australia Women tour of Sri Lanka, 2026", "1st ODI", "ODI", "Sri Lanka Women", "Australia Women", "2026-12-15", "10:00 IST", "Rangiri Dambulla International Stadium, Dambulla"),
    ("Bangladesh Women tour of New Zealand, 2026", "3rd T20I", "T20I", "New Zealand Women", "Bangladesh Women", "2026-12-15", "20:00 NZDT", "Sky Stadium, Wellington"),
    ("India Women tour of South Africa, 2026", "1st ODI", "ODI", "South Africa Women", "India Women", "2026-12-16", "10:00 SAST", "Boland Park, Paarl"),
    ("Bangladesh Women tour of New Zealand, 2026", "1st ODI", "ODI", "New Zealand Women", "Bangladesh Women", "2026-12-18", "15:00 NZDT", "Sky Stadium, Wellington"),
    ("Australia Women tour of Sri Lanka, 2026", "2nd ODI", "ODI", "Sri Lanka Women", "Australia Women", "2026-12-18", "10:00 IST", "Rangiri Dambulla International Stadium, Dambulla"),
    ("India Women tour of South Africa, 2026", "2nd ODI", "ODI", "South Africa Women", "India Women", "2026-12-19", "14:00 SAST", "Newlands, Cape Town"),
    ("Australia Women tour of Sri Lanka, 2026", "3rd ODI", "ODI", "Sri Lanka Women", "Australia Women", "2026-12-20", "10:00 IST", "Rangiri Dambulla International Stadium, Dambulla"),
    ("Bangladesh Women tour of New Zealand, 2026", "2nd ODI", "ODI", "New Zealand Women", "Bangladesh Women", "2026-12-21", "15:00 NZDT", "Bay Oval, Mount Maunganui"),
    ("India Women tour of South Africa, 2026", "3rd ODI", "ODI", "South Africa Women", "India Women", "2026-12-22", "14:00 SAST", "Mangaung Oval, Bloemfontein"),
    ("Bangladesh Women tour of New Zealand, 2026", "3rd ODI", "ODI", "New Zealand Women", "Bangladesh Women", "2026-12-23", "15:00 NZDT", "Bay Oval, Mount Maunganui"),
    ("India Women tour of South Africa, 2026", "1st T20I", "T20I", "South Africa Women", "India Women", "2026-12-26", "18:00 SAST", "Willowmoore Park, Benoni"),
    ("India Women tour of South Africa, 2026", "2nd T20I", "T20I", "South Africa Women", "India Women", "2026-12-29", "18:00 SAST", "Senwes Park, Potchefstroom"),
    ("India Women tour of South Africa, 2026", "3rd T20I", "T20I", "South Africa Women", "India Women", "2026-12-30", "18:00 SAST", "Senwes Park, Potchefstroom"),
)


def main():
    with SessionLocal() as db:
        teams = {}
        for name, code, country in TEAMS:
            item = db.scalar(select(Team).where(func.lower(Team.name) == name.lower()))
            if item is None:
                item = Team(name=name, short_name=code, country=country, category="Women's National Team")
                db.add(item); db.flush()
            teams[name] = item
        series_map = {}
        for name, start, end, members in SERIES:
            item = db.scalar(select(Series).where(func.lower(Series.name) == name.lower()))
            if item is None:
                item = Series(name=name, category="Women's International", start_date=date.fromisoformat(start), end_date=date.fromisoformat(end))
                db.add(item); db.flush()
            for member in members:
                if db.scalar(select(SeriesTeamMembership).where(SeriesTeamMembership.series_id == item.id, SeriesTeamMembership.team_id == teams[member].id)) is None:
                    db.add(SeriesTeamMembership(series_id=item.id, team_id=teams[member].id, is_active=True))
            series_map[name] = item
        added = 0
        for series_name, stage, match_format, one, two, day, start_time, venue in FIXTURES:
            match_date = date.fromisoformat(day)
            if db.scalar(select(Match).where(Match.series == series_name, Match.stage == stage, Match.date == match_date)) is None:
                first, second = teams[one], teams[two]
                db.add(Match(series=series_name, series_id=series_map[series_name].id, stage=stage, status="Upcoming", team1=one, team1_code=first.short_name, team1_id=first.id, team2=two, team2_code=second.short_name, team2_id=second.id, date=match_date, time=start_time, venue=venue, format=match_format, result="", toss=""))
                added += 1
        db.commit()
    print(f"Verified Cricket Hub batch 3 complete; {added} matches inserted.")


if __name__ == "__main__":
    main()
