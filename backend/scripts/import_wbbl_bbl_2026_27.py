"""Idempotently import the supplied WBBL|12 and BBL|16 regular-season fixtures."""
from datetime import date
from sqlalchemy import and_, func, select
from backend.app.database import SessionLocal
from backend.app.models import Match, Series, SeriesTeamMembership, Team

WBBL = "Women's Big Bash League 2026"
BBL = "Big Bash League 2026–27"
TEAMS = {
    'MRW':('Melbourne Renegades Women','MRW',"Women's T20 Franchise"),'BHW':('Brisbane Heat Women','BHW',"Women's T20 Franchise"),'STW':('Sydney Thunder Women','STW',"Women's T20 Franchise"),'ASW':('Adelaide Strikers Women','ASW',"Women's T20 Franchise"),'SSW':('Sydney Sixers Women','SSW',"Women's T20 Franchise"),'MSW':('Melbourne Stars Women','MSW',"Women's T20 Franchise"),'PSW':('Perth Scorchers Women','PSW',"Women's T20 Franchise"),'HHW':('Hobart Hurricanes Women','HHW',"Women's T20 Franchise"),
    'MR':('Melbourne Renegades','MR',"Men's T20 Franchise"),'PS':('Perth Scorchers','PS',"Men's T20 Franchise"),'BH':('Brisbane Heat','BH',"Men's T20 Franchise"),'SS':('Sydney Sixers','SS',"Men's T20 Franchise"),'ST':('Sydney Thunder','ST',"Men's T20 Franchise"),'AS':('Adelaide Strikers','AS',"Men's T20 Franchise"),'HH':('Hobart Hurricanes','HH',"Men's T20 Franchise"),'MS':('Melbourne Stars','MS',"Men's T20 Franchise"),
}
# number|date|team1|team2|venue. Start times were not supplied as verified and remain blank.
W_FIXTURES = '''33|2026-11-25|MRW|BHW|Junction Oval, Melbourne
34|2026-11-26|STW|ASW|North Sydney Oval, Sydney
35|2026-11-26|SSW|MSW|North Sydney Oval, Sydney
36|2026-11-27|PSW|HHW|WACA Ground, Perth
37|2026-11-28|MRW|MSW|Junction Oval, Melbourne
38|2026-11-28|STW|SSW|Drummoyne Oval, Sydney
39|2026-11-29|BHW|PSW|Karen Rolton Oval, Adelaide
40|2026-11-29|ASW|HHW|Karen Rolton Oval, Adelaide'''
B_FIXTURES = '''1|2026-12-12|MR|PS|MA Chidambaram Stadium, Chennai
2|2026-12-15|BH|SS|The Gabba, Brisbane
3|2026-12-16|ST|AS|Manuka Oval, Canberra
4|2026-12-17|HH|BH|Bellerive Oval, Hobart
5|2026-12-18|MS|AS|MCG, Melbourne
6|2026-12-19|ST|SS|Sydney Showground Stadium, Sydney
7|2026-12-20|PS|HH|Perth Stadium, Perth
8|2026-12-21|MS|BH|Junction Oval, Melbourne
9|2026-12-22|SS|MR|SCG, Sydney
10|2026-12-23|AS|ST|Adelaide Oval, Adelaide
11|2026-12-24|HH|MR|Junction Oval, Melbourne
12|2026-12-26|BH|SS|SCG, Sydney
13|2026-12-26|MS|PS|Perth Stadium, Perth
14|2026-12-27|ST|MR|Sydney Showground Stadium, Sydney
15|2026-12-28|BH|AS|The Gabba, Brisbane
16|2026-12-29|HH|MS|Bellerive Oval, Hobart
17|2026-12-30|PS|ST|Perth Stadium, Perth
18|2026-12-31|AS|MS|Adelaide Oval, Adelaide
19|2027-01-01|MR|SS|MCG, Melbourne
20|2027-01-01|BH|HH|The Gabba, Brisbane
21|2027-01-02|ST|PS|Sydney Showground Stadium, Sydney
22|2027-01-03|SS|AS|Manuka Oval, Canberra
23|2027-01-04|MS|MR|MCG, Melbourne
24|2027-01-04|PS|BH|Perth Stadium, Perth
25|2027-01-05|HH|ST|Bellerive Oval, Hobart
26|2027-01-06|AS|MR|Adelaide Oval, Adelaide
27|2027-01-07|MS|SS|MCG, Melbourne
28|2027-01-08|BH|PS|The Gabba, Brisbane
29|2027-01-09|HH|AS|Launceston, Tasmania
30|2027-01-10|SS|PS|SCG, Sydney
31|2027-01-10|MR|BH|Junction Oval, Melbourne
32|2027-01-11|ST|MS|Manuka Oval, Canberra
33|2027-01-12|AS|HH|Adelaide Oval, Adelaide
34|2027-01-13|PS|MR|Perth Stadium, Perth
35|2027-01-14|MS|HH|MCG, Melbourne
36|2027-01-15|SS|ST|SCG, Sydney
37|2027-01-16|AS|PS|Adelaide Oval, Adelaide
38|2027-01-16|MR|MS|MCG, Melbourne
39|2027-01-17|HH|SS|Bellerive Oval, Hobart
40|2027-01-17|BH|ST|The Gabba, Brisbane'''

def rows(raw): return [line.split('|') for line in raw.splitlines()]
def main():
  inserted=existing=0
  with SessionLocal() as db:
    masters={}
    for key,(name,code,category) in TEAMS.items():
      item=db.scalar(select(Team).where(func.lower(Team.name)==name.lower()))
      if item is None: item=Team(name=name,short_name=code,country='Australia',category=category);db.add(item);db.flush()
      masters[key]=item
    for series_name,start,end,raw in ((WBBL,'2026-10-29','2026-12-05',W_FIXTURES),(BBL,'2026-12-12','2027-01-26',B_FIXTURES)):
      series=db.scalar(select(Series).where(func.lower(Series.name)==series_name.lower()))
      if series is None: series=Series(name=series_name,category='T20 League',start_date=date.fromisoformat(start),end_date=date.fromisoformat(end));db.add(series);db.flush()
      used={x for _,_,x,y,_ in rows(raw) for x in (x,y)}
      for key in used:
        if db.scalar(select(SeriesTeamMembership).where(and_(SeriesTeamMembership.series_id==series.id,SeriesTeamMembership.team_id==masters[key].id))) is None: db.add(SeriesTeamMembership(series_id=series.id,team_id=masters[key].id,is_active=True))
      for number,day,one,two,venue in rows(raw):
        found=db.scalar(select(Match).where(and_(Match.series==series_name,Match.date==date.fromisoformat(day),Match.team1==masters[one].name,Match.team2==masters[two].name,Match.venue==venue)))
        if found: existing+=1; continue
        db.add(Match(series=series_name,series_id=series.id,stage=f'Match {number}',status='Upcoming',team1=masters[one].name,team1_code=masters[one].short_name,team1_id=masters[one].id,team2=masters[two].name,team2_code=masters[two].short_name,team2_id=masters[two].id,date=date.fromisoformat(day),time='',venue=venue,format='T20',result='',toss=''));inserted+=1
    db.commit()
  print(f'WBBL/BBL import: inserted={inserted}, existing={existing}, skipped_playoffs=7')
if __name__=='__main__': main()
