"""Idempotently load verified Cricket Hub data batch 1.

Uses the database selected by DATABASE_URL.  On a deployment this must point
to PostgreSQL; locally the application defaults to SQLite.
"""

from datetime import date

from sqlalchemy import func, select

from backend.app.database import SessionLocal
from backend.app.models import Match, Series, SeriesTeamMembership, Team


TEAM_ROWS = (
    ("Australia", "AUS", "Australia", "Men's National Team"),
    ("England", "ENG", "England", "Men's National Team"),
    ("South Africa", "SA", "South Africa", "Men's National Team"),
    ("Bangladesh", "BAN", "Bangladesh", "Men's National Team"),
    ("India", "IND", "India", "Men's National Team"),
    ("Sri Lanka", "SL", "Sri Lanka", "Men's National Team"),
    ("Zimbabwe", "ZIM", "Zimbabwe", "Men's National Team"),
    ("New Zealand", "NZ", "New Zealand", "Men's National Team"),
    ("Abu Dhabi Knight Riders", "ADKR", "United Arab Emirates", "T20 Franchise"),
    ("Desert Vipers", "DV", "United Arab Emirates", "T20 Franchise"),
    ("Dubai Capitals", "DC", "United Arab Emirates", "T20 Franchise"),
    ("Gulf Giants", "GG", "United Arab Emirates", "T20 Franchise"),
    ("MI Emirates", "MIE", "United Arab Emirates", "T20 Franchise"),
    ("Sharjah Warriorz", "SW", "United Arab Emirates", "T20 Franchise"),
)

SERIES_ROWS = (
    ("England tour of Australia, 2026", "Men's International", "2026-11-13", "2026-12-02", ("Australia", "England")),
    ("Bangladesh tour of South Africa, 2026", "Men's International", "2026-11-15", "2026-12-13", ("South Africa", "Bangladesh")),
    ("Sri Lanka tour of India, 2026", "Men's International", "2026-12-13", "2026-12-27", ("India", "Sri Lanka")),
    ("Zimbabwe tour of India, 2027", "Men's International", "2027-01-03", "2027-01-09", ("India", "Zimbabwe")),
    ("England tour of South Africa, 2026–27", "Men's International", "2026-12-17", "2027-01-15", ("South Africa", "England")),
    ("Sri Lanka tour of New Zealand, 2027 (ODI & T20I)", "Men's International", "2027-01-16", "2027-01-31", ("New Zealand", "Sri Lanka")),
    ("International League T20, 2026", "T20 League", "2026-11-21", "2026-12-20", ("Abu Dhabi Knight Riders", "Desert Vipers", "Dubai Capitals", "Gulf Giants", "MI Emirates", "Sharjah Warriorz")),
)

# Series, stage, format, team 1, team 2, date, local time, venue.
# “Unverified” is intentional where a start time was not confirmed.
MATCH_ROWS = (
    ("England tour of Australia, 2026", "2nd T20I", "T20I", "Australia", "England", "2026-11-24", "18:15 AEST", "Carrara Oval, Queensland"),
    ("England tour of Australia, 2026", "3rd T20I", "T20I", "Australia", "England", "2026-11-27", "18:15 AEST", "The Gabba, Brisbane"),
    ("England tour of Australia, 2026", "4th T20I", "T20I", "Australia", "England", "2026-11-29", "19:15 AEDT", "Sydney Cricket Ground, Sydney"),
    ("Bangladesh tour of South Africa, 2026", "1st ODI", "ODI", "South Africa", "Bangladesh", "2026-12-01", "Unverified", "Buffalo Park Cricket Stadium, East London"),
    ("England tour of Australia, 2026", "5th T20I", "T20I", "Australia", "England", "2026-12-02", "19:15 AEDT", "Manuka Oval, Canberra"),
    ("Bangladesh tour of South Africa, 2026", "2nd ODI", "ODI", "South Africa", "Bangladesh", "2026-12-04", "Unverified", "St George's Park, Gqeberha"),
    ("Bangladesh tour of South Africa, 2026", "3rd ODI", "ODI", "South Africa", "Bangladesh", "2026-12-07", "Unverified", "Newlands Cricket Ground, Cape Town"),
    ("Bangladesh tour of South Africa, 2026", "1st T20I", "T20I", "South Africa", "Bangladesh", "2026-12-10", "Unverified", "Kimberley Oval, Kimberley"),
    ("Bangladesh tour of South Africa, 2026", "2nd T20I", "T20I", "South Africa", "Bangladesh", "2026-12-12", "Unverified", "Willowmoore Park, Benoni"),
    ("Sri Lanka tour of India, 2026", "1st ODI", "ODI", "India", "Sri Lanka", "2026-12-13", "14:00 IST", "Arun Jaitley Stadium, Delhi"),
    ("Bangladesh tour of South Africa, 2026", "3rd T20I", "T20I", "South Africa", "Bangladesh", "2026-12-13", "Unverified", "SuperSport Park, Centurion"),
    ("Sri Lanka tour of India, 2026", "2nd ODI", "ODI", "India", "Sri Lanka", "2026-12-16", "14:00 IST", "M. Chinnaswamy Stadium, Bengaluru"),
    ("Sri Lanka tour of India, 2026", "3rd ODI", "ODI", "India", "Sri Lanka", "2026-12-19", "14:00 IST", "Narendra Modi Stadium, Ahmedabad"),
    ("Sri Lanka tour of India, 2026", "1st T20I", "T20I", "India", "Sri Lanka", "2026-12-22", "19:00 IST", "Niranjan Shah Stadium, Rajkot"),
    ("Sri Lanka tour of India, 2026", "2nd T20I", "T20I", "India", "Sri Lanka", "2026-12-24", "19:00 IST", "Barabati Stadium, Cuttack"),
    ("Sri Lanka tour of India, 2026", "3rd T20I", "T20I", "India", "Sri Lanka", "2026-12-27", "19:00 IST", "Maharashtra Cricket Association Stadium, Pune"),
    ("Zimbabwe tour of India, 2027", "1st ODI", "ODI", "India", "Zimbabwe", "2027-01-03", "14:00 IST", "Eden Gardens, Kolkata"),
    ("Zimbabwe tour of India, 2027", "2nd ODI", "ODI", "India", "Zimbabwe", "2027-01-06", "14:00 IST", "Rajiv Gandhi International Stadium, Hyderabad"),
    ("Zimbabwe tour of India, 2027", "3rd ODI", "ODI", "India", "Zimbabwe", "2027-01-09", "14:00 IST", "Wankhede Stadium, Mumbai"),
    ("England tour of South Africa, 2026–27", "1st ODI", "ODI", "South Africa", "England", "2027-01-10", "10:00 SAST", "Boland Park, Paarl"),
    ("England tour of South Africa, 2026–27", "2nd ODI", "ODI", "South Africa", "England", "2027-01-13", "13:30 SAST", "Mangaung Oval, Bloemfontein"),
    ("England tour of South Africa, 2026–27", "3rd ODI", "ODI", "South Africa", "England", "2027-01-15", "10:00 SAST", "Mangaung Oval, Bloemfontein"),
    ("Sri Lanka tour of New Zealand, 2027 (ODI & T20I)", "1st ODI", "ODI", "New Zealand", "Sri Lanka", "2027-01-16", "11:00 NZDT", "McLean Park, Napier"),
    ("Sri Lanka tour of New Zealand, 2027 (ODI & T20I)", "2nd ODI", "ODI", "New Zealand", "Sri Lanka", "2027-01-19", "11:00 NZDT", "Basin Reserve, Wellington"),
    ("Sri Lanka tour of New Zealand, 2027 (ODI & T20I)", "3rd ODI", "ODI", "New Zealand", "Sri Lanka", "2027-01-22", "11:00 NZDT", "University Oval, Dunedin"),
    ("Sri Lanka tour of New Zealand, 2027 (ODI & T20I)", "1st T20I", "T20I", "New Zealand", "Sri Lanka", "2027-01-26", "18:00 NZDT", "Hagley Oval, Christchurch"),
    ("Sri Lanka tour of New Zealand, 2027 (ODI & T20I)", "2nd T20I", "T20I", "New Zealand", "Sri Lanka", "2027-01-29", "16:00 NZDT", "Saxton Oval, Nelson"),
    ("Sri Lanka tour of New Zealand, 2027 (ODI & T20I)", "3rd T20I", "T20I", "New Zealand", "Sri Lanka", "2027-01-31", "13:00 NZDT", "Saxton Oval, Nelson"),
    ("International League T20, 2026", "Match 5", "T20", "Gulf Giants", "MI Emirates", "2026-11-24", "18:30 GST", "Dubai International Stadium, Dubai"),
    ("International League T20, 2026", "Match 6", "T20", "Dubai Capitals", "Desert Vipers", "2026-11-25", "18:30 GST", "Dubai International Stadium, Dubai"),
    ("International League T20, 2026", "Match 7", "T20", "Abu Dhabi Knight Riders", "MI Emirates", "2026-11-26", "18:30 GST", "Sheikh Zayed Cricket Stadium, Abu Dhabi"),
    ("International League T20, 2026", "Match 8", "T20", "Sharjah Warriorz", "Dubai Capitals", "2026-11-27", "18:30 GST", "Sharjah Cricket Stadium, Sharjah"),
    ("International League T20, 2026", "Match 9", "T20", "MI Emirates", "Desert Vipers", "2026-11-28", "14:00 GST", "Sheikh Zayed Cricket Stadium, Abu Dhabi"),
    ("International League T20, 2026", "Match 10", "T20", "Gulf Giants", "Dubai Capitals", "2026-11-28", "18:30 GST", "Dubai International Stadium, Dubai"),
    ("International League T20, 2026", "Match 11", "T20", "Abu Dhabi Knight Riders", "Sharjah Warriorz", "2026-11-29", "18:30 GST", "Sheikh Zayed Cricket Stadium, Abu Dhabi"),
    ("International League T20, 2026", "Match 12", "T20", "Desert Vipers", "Gulf Giants", "2026-11-29", "18:30 GST", "Dubai International Stadium, Dubai"),
    ("International League T20, 2026", "Match 13", "T20", "MI Emirates", "Abu Dhabi Knight Riders", "2026-11-30", "18:30 GST", "Sheikh Zayed Cricket Stadium, Abu Dhabi"),
    ("International League T20, 2026", "Match 14", "T20", "Gulf Giants", "Sharjah Warriorz", "2026-12-01", "18:30 GST", "Sharjah Cricket Stadium, Sharjah"),
    ("International League T20, 2026", "Match 15", "T20", "Abu Dhabi Knight Riders", "Desert Vipers", "2026-12-02", "14:00 GST", "Sheikh Zayed Cricket Stadium, Abu Dhabi"),
    ("International League T20, 2026", "Match 16", "T20", "Dubai Capitals", "MI Emirates", "2026-12-02", "18:30 GST", "Dubai International Stadium, Dubai"),
    ("International League T20, 2026", "Match 17", "T20", "Gulf Giants", "Abu Dhabi Knight Riders", "2026-12-03", "18:30 GST", "Dubai International Stadium, Dubai"),
    ("International League T20, 2026", "Match 18", "T20", "Desert Vipers", "Sharjah Warriorz", "2026-12-04", "18:30 GST", "Sharjah Cricket Stadium, Sharjah"),
    ("International League T20, 2026", "Match 19", "T20", "Abu Dhabi Knight Riders", "Gulf Giants", "2026-12-05", "18:30 GST", "Sheikh Zayed Cricket Stadium, Abu Dhabi"),
    ("International League T20, 2026", "Match 20", "T20", "MI Emirates", "Sharjah Warriorz", "2026-12-06", "14:00 GST", "Sheikh Zayed Cricket Stadium, Abu Dhabi"),
    ("International League T20, 2026", "Match 21", "T20", "Desert Vipers", "Dubai Capitals", "2026-12-06", "18:30 GST", "Dubai International Stadium, Dubai"),
    ("International League T20, 2026", "Match 22", "T20", "MI Emirates", "Gulf Giants", "2026-12-07", "18:30 GST", "Sheikh Zayed Cricket Stadium, Abu Dhabi"),
    ("International League T20, 2026", "Match 23", "T20", "Dubai Capitals", "Sharjah Warriorz", "2026-12-08", "18:30 GST", "Dubai International Stadium, Dubai"),
    ("International League T20, 2026", "Match 24", "T20", "Sharjah Warriorz", "Abu Dhabi Knight Riders", "2026-12-09", "18:30 GST", "Sharjah Cricket Stadium, Sharjah"),
    ("International League T20, 2026", "Match 25", "T20", "Dubai Capitals", "Gulf Giants", "2026-12-10", "18:30 GST", "Dubai International Stadium, Dubai"),
    ("International League T20, 2026", "Match 26", "T20", "Sharjah Warriorz", "MI Emirates", "2026-12-11", "18:30 GST", "Sharjah Cricket Stadium, Sharjah"),
    ("International League T20, 2026", "Match 27", "T20", "Desert Vipers", "Abu Dhabi Knight Riders", "2026-12-12", "18:30 GST", "Dubai International Stadium, Dubai"),
    ("International League T20, 2026", "Match 28", "T20", "MI Emirates", "Dubai Capitals", "2026-12-13", "14:00 GST", "Sheikh Zayed Cricket Stadium, Abu Dhabi"),
    ("International League T20, 2026", "Match 29", "T20", "Gulf Giants", "Desert Vipers", "2026-12-13", "18:30 GST", "Dubai International Stadium, Dubai"),
    ("International League T20, 2026", "Match 30", "T20", "Abu Dhabi Knight Riders", "Dubai Capitals", "2026-12-14", "18:30 GST", "Sheikh Zayed Cricket Stadium, Abu Dhabi"),
)


def get_or_create_team(db, name, code, country, category):
    team = db.scalar(select(Team).where(func.lower(Team.name) == name.lower()))
    if team is None:
        team = Team(name=name, short_name=code, country=country, category=category)
        db.add(team)
        db.flush()
    return team


def main():
    with SessionLocal() as db:
        teams = {name: get_or_create_team(db, name, code, country, category) for name, code, country, category in TEAM_ROWS}
        series_by_name = {}
        for name, category, start, end, members in SERIES_ROWS:
            series = db.scalar(select(Series).where(func.lower(Series.name) == name.lower()))
            if series is None:
                series = Series(name=name, category=category, start_date=date.fromisoformat(start), end_date=date.fromisoformat(end))
                db.add(series)
                db.flush()
            for team_name in members:
                if db.scalar(select(SeriesTeamMembership).where(SeriesTeamMembership.series_id == series.id, SeriesTeamMembership.team_id == teams[team_name].id)) is None:
                    db.add(SeriesTeamMembership(series_id=series.id, team_id=teams[team_name].id, is_active=True))
            series_by_name[name] = series

        inserted = 0
        for series_name, stage, match_format, first, second, day, start_time, venue in MATCH_ROWS:
            match_date = date.fromisoformat(day)
            existing = db.scalar(select(Match).where(Match.series == series_name, Match.stage == stage, Match.date == match_date))
            if existing is None:
                team1, team2 = teams[first], teams[second]
                db.add(Match(series=series_name, series_id=series_by_name[series_name].id, stage=stage, status="Upcoming", team1=first, team1_code=team1.short_name, team1_id=team1.id, team2=second, team2_code=team2.short_name, team2_id=team2.id, date=match_date, time=start_time, venue=venue, format=match_format, result="", toss=""))
                inserted += 1
        db.commit()
    print(f"Verified Cricket Hub batch 1 complete; {inserted} matches inserted.")


if __name__ == "__main__":
    main()
