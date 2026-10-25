"""Retrieve ESPN-reported NBA injuries. Missing/partial feed is never treated as healthy."""
import csv,json,urllib.request
from datetime import datetime,timezone
from pathlib import Path
DATA=Path(__file__).resolve().parents[1]/"data"
URL="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
def main():
    req=urllib.request.Request(URL,headers={"User-Agent":"NBAEdgeResearch/1.0"})
    with urllib.request.urlopen(req,timeout=25) as response:payload=json.load(response)
    rows=[]
    for team in payload.get("injuries",[]):
        team_name=team.get("displayName") or team.get("team",{}).get("displayName","")
        for item in team.get("injuries",[]):
            athlete=item.get("athlete",{})
            rows.append({"team":team_name,"player":athlete.get("displayName",""),
                         "status":item.get("status",""),"details":str(item.get("details",""))[:500],
                         "captured_utc":datetime.now(timezone.utc).isoformat(),"source":"ESPN"})
    if not payload.get("injuries"):
        raise RuntimeError("No injuries array returned; preserve previous snapshot instead of implying no injuries")
    with (DATA/"injuries.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=["team","player","status","details","captured_utc","source"])
        writer.writeheader();writer.writerows(rows)
if __name__=="__main__":main()
