"""Load verified Syed Mushtaq Ali Trophy Elite group fixtures (batch 2)."""

from datetime import date

from sqlalchemy import func, select

from backend.app.database import SessionLocal
from backend.app.models import Match, Series, SeriesTeamMembership, Team


SERIES_NAME = "Syed Mushtaq Ali Trophy – Elite, 2026"
GROUPS = {
    "A": ("Mumbai", ("Bengal", "Baroda", "Chandigarh", "Jharkhand", "Karnataka", "Mizoram", "Rajasthan", "Uttar Pradesh")),
    "B": ("Visakhapatnam", ("Bihar", "Delhi", "Haryana", "Jammu and Kashmir", "Punjab", "Railways", "Saurashtra", "Tamil Nadu")),
    "C": ("Kolkata", ("Andhra", "Assam", "Himachal Pradesh", "Kerala", "Madhya Pradesh", "Maharashtra", "Puducherry", "Tripura")),
    "D": ("Mohali", ("Chhattisgarh", "Goa", "Gujarat", "Hyderabad", "Mumbai", "Odisha", "Uttarakhand", "Vidarbha")),
}
CODES = {"Andhra":"AND", "Assam":"ASM", "Baroda":"BRD", "Bengal":"BEN", "Bihar":"BIH", "Chandigarh":"CDG", "Chhattisgarh":"CHA", "Delhi":"DEL", "Goa":"GOA", "Gujarat":"GUJ", "Haryana":"HAR", "Himachal Pradesh":"HP", "Hyderabad":"HYD", "Jammu and Kashmir":"J&K", "Jharkhand":"JHK", "Karnataka":"KAR", "Kerala":"KER", "Madhya Pradesh":"MP", "Maharashtra":"MAH", "Mizoram":"MIZ", "Mumbai":"MUM", "Odisha":"ODS", "Puducherry":"PUD", "Punjab":"PUN", "Railways":"RLY", "Rajasthan":"RAJ", "Saurashtra":"SAU", "Tamil Nadu":"TN", "Tripura":"TRI", "Uttar Pradesh":"UP", "Uttarakhand":"UTK", "Vidarbha":"VID"}

# Date, group, fixture number, team 1, team 2, confirmed IST start time.
FIXTURES = (
    ("2026-11-24","A",1,"Bengal","Uttar Pradesh","09:00 IST"),("2026-11-24","A",2,"Chandigarh","Mizoram","11:00 IST"),("2026-11-24","A",3,"Karnataka","Rajasthan","13:30 IST"),("2026-11-24","A",4,"Jharkhand","Baroda","16:30 IST"),
    ("2026-11-24","B",1,"Delhi","Tamil Nadu","09:00 IST"),("2026-11-24","B",2,"Punjab","Saurashtra","11:00 IST"),("2026-11-24","B",3,"Jammu and Kashmir","Railways","13:30 IST"),("2026-11-24","B",4,"Bihar","Haryana","16:30 IST"),
    ("2026-11-24","C",1,"Kerala","Assam","09:00 IST"),("2026-11-24","C",2,"Maharashtra","Tripura","11:00 IST"),("2026-11-24","C",3,"Madhya Pradesh","Himachal Pradesh","13:30 IST"),("2026-11-24","C",4,"Andhra","Puducherry","16:30 IST"),
    ("2026-11-24","D",1,"Chhattisgarh","Goa","09:00 IST"),("2026-11-24","D",2,"Hyderabad","Gujarat","11:00 IST"),("2026-11-24","D",3,"Uttarakhand","Vidarbha","13:30 IST"),("2026-11-24","D",4,"Odisha","Mumbai","16:30 IST"),
    ("2026-11-26","A",5,"Karnataka","Baroda","09:00 IST"),("2026-11-26","A",6,"Bengal","Rajasthan","11:00 IST"),("2026-11-26","A",7,"Chandigarh","Jharkhand","13:30 IST"),("2026-11-26","A",8,"Mizoram","Uttar Pradesh","16:30 IST"),
    ("2026-11-26","B",5,"Jammu and Kashmir","Haryana","09:00 IST"),("2026-11-26","B",6,"Delhi","Railways","11:00 IST"),("2026-11-26","B",7,"Punjab","Bihar","13:30 IST"),("2026-11-26","B",8,"Saurashtra","Tamil Nadu","16:30 IST"),
    ("2026-11-26","C",5,"Kerala","Himachal Pradesh","11:00 IST"),("2026-11-26","C",6,"Maharashtra","Andhra","13:30 IST"),("2026-11-26","C",7,"Tripura","Assam","16:30 IST"),("2026-11-26","C",8,"Madhya Pradesh","Puducherry","09:00 IST"),
    ("2026-11-26","D",5,"Uttarakhand","Mumbai","09:00 IST"),("2026-11-26","D",6,"Chhattisgarh","Vidarbha","11:00 IST"),("2026-11-26","D",7,"Hyderabad","Odisha","13:30 IST"),("2026-11-26","D",8,"Gujarat","Goa","16:30 IST"),
)


def main():
    with SessionLocal() as db:
        teams = {}
        for _, members in GROUPS.values():
            for name in members:
                team = db.scalar(select(Team).where(func.lower(Team.name) == name.lower()))
                if team is None:
                    team = Team(name=name, short_name=CODES[name], country="India", category="Domestic State Team")
                    db.add(team); db.flush()
                teams[name] = team
        series = db.scalar(select(Series).where(func.lower(Series.name) == SERIES_NAME.lower()))
        if series is None:
            series = Series(name=SERIES_NAME, category="Domestic T20", start_date=date(2026, 11, 14), end_date=date(2026, 12, 6))
            db.add(series); db.flush()
        for team in teams.values():
            if db.scalar(select(SeriesTeamMembership).where(SeriesTeamMembership.series_id == series.id, SeriesTeamMembership.team_id == team.id)) is None:
                db.add(SeriesTeamMembership(series_id=series.id, team_id=team.id, is_active=True))
        added = 0
        for day, group, number, first, second, start_time in FIXTURES:
            stage = f"Elite Group {group} – Match {number}"
            match_date = date.fromisoformat(day)
            if db.scalar(select(Match).where(Match.series == SERIES_NAME, Match.stage == stage, Match.date == match_date)) is None:
                venue_city = GROUPS[group][0]
                db.add(Match(series=SERIES_NAME, series_id=series.id, stage=stage, status="Upcoming", team1=first, team1_code=teams[first].short_name, team1_id=teams[first].id, team2=second, team2_code=teams[second].short_name, team2_id=teams[second].id, date=match_date, time=start_time, venue=f"{venue_city} (exact ground unverified)", format="T20", result="", toss=""))
                added += 1
        db.commit()
    print(f"Verified Cricket Hub batch 2 complete; {added} matches inserted.")


if __name__ == "__main__":
    main()
