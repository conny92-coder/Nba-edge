"""Daily NBA scoreboard ingest and conservative rating update. Public ESPN scoreboard API."""
import csv, json
try:
    from .feed_utils import fetch_json, write_rows, atomic_text
except ImportError:
    from feed_utils import fetch_json, write_rows, atomic_text
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
TEAMS={"ATL","BOS","BKN","CHA","CHI","CLE","DAL","DEN","DET","GSW","HOU","IND","LAC","LAL","MEM","MIA","MIL","MIN","NOP","NYK","OKC","ORL","PHI","PHX","POR","SAC","SAS","TOR","UTA","WAS"}
def read_rows(path):
    if not path.exists(): return []
    with path.open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))
def collect(date):
    data=fetch_json("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates="+date)
    rows=[]
    for event in data.get("events",[]):
        comps=event.get("competitions",[])
        if not comps: continue
        comp=comps[0]; sides={t.get("homeAway"):t for t in comp.get("competitors",[])}
        if not all(x in sides for x in ("home","away")): continue
        home,away=sides["home"],sides["away"]
        status=event.get("status",{}).get("type",{})
        if not status.get("completed"): continue
        ha=home.get("team",{}).get("abbreviation","").upper()
        aa=away.get("team",{}).get("abbreviation","").upper()
        aliases={'GS':'GSW','NY':'NYK','NO':'NOP','SA':'SAS','UTAH':'UTA','WSH':'WAS','PHO':'PHX'}
        ha,aa=aliases.get(ha,ha),aliases.get(aa,aa)
        if ha not in TEAMS or aa not in TEAMS: continue
        try: hp=int(home["score"]);ap=int(away["score"])
        except (ValueError,KeyError,TypeError):continue
        rows.append({"game_id":event["id"],"date_utc":event.get("date",""),"away":aa,"home":ha,"away_score":ap,"home_score":hp,"source":"ESPN scoreboard"})
    return rows
def main():
    now=datetime.now(timezone.utc)
    existing={str(r["game_id"]):r for r in read_rows(DATA/"game_results.csv")}
    dates=[(now-timedelta(days=i)).strftime("%Y%m%d") for i in range(4)]
    errors=[]
    for day in dates:
        try:
            for row in collect(day):existing[str(row["game_id"])]=row
        except Exception as exc:errors.append(f"{day}: {exc}")
    results=sorted(existing.values(),key=lambda x:(x["date_utc"],x["game_id"]))
    write_rows(DATA/"game_results.csv",["game_id","date_utc","away","home","away_score","home_score","source"],results)
    # Derive current team ratings from baseline, replaying unique games in chronological order.
    # Score-margin learning is an explicitly provisional approximation, NOT possession-adjusted efficiency.
    baseline=read_rows(DATA/"power_ratings.csv")
    ratings={r.get("Code",""):r for r in baseline}
    adjustments={team:0.0 for team in ratings}
    games_played={team:0 for team in ratings}
    for game in results:
        a,h=game["away"],game["home"]
        if a not in ratings or h not in ratings:continue
        margin=float(game["home_score"])-float(game["away_score"])
        prior_home=float(ratings[h].get("Live Net",0))+adjustments[h]
        prior_away=float(ratings[a].get("Live Net",0))+adjustments[a]
        error=max(-25,min(25,margin-(prior_home-prior_away+2.0)))
        step=0.10*error/2
        adjustments[h]+=step;adjustments[a]-=step
        games_played[h]+=1;games_played[a]+=1
    out=[]
    for code,r in ratings.items():
        out.append({"Code":code,"Team":r.get("Team",""),"Baseline Net":r.get("Live Net",""),
                    "Result Adjustment":round(adjustments[code],3),
                    "Updated Net":round(float(r.get("Live Net",0))+adjustments[code],3),
                    "Recorded Games":games_played[code]})
    write_rows(DATA/"updated_ratings.csv",["Code","Team","Baseline Net","Result Adjustment","Updated Net","Recorded Games"],out)
    status={"last_attempt_utc":now.isoformat(),"completed_games":len(results),"source":"ESPN scoreboard","errors":errors,
            "ratings_method":"Provisional score-margin residual; baseline + replayed adjustments; NOT box-score efficiency"}
    atomic_text(DATA/"refresh_status.json",json.dumps(status,indent=2)+"\n")
    if errors: print("Results feed unavailable; retained existing games: " + "; ".join(errors))
    return not errors
if __name__=="__main__":main()
