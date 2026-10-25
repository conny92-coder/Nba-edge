import csv
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

data = Path(__file__).resolve().parents[1] / "data"
with (data / "power_ratings.csv").open() as f:
    ratings = {r["Code"]: float(r["Live Net"]) for r in csv.DictReader(f)}
if (data / "updated_ratings.csv").exists():
    with (data / "updated_ratings.csv").open() as f:
        ratings.update({r["Code"]: float(r["Updated Net"]) for r in csv.DictReader(f)})
day = datetime.now(timezone.utc).strftime("%Y%m%d")
url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=" + day
req = urllib.request.Request(url, headers={"User-Agent": "NBAEdgeResearch/1.0"})
with urllib.request.urlopen(req, timeout=25) as f:
    events = json.load(f).get("events", [])
output = []
for event in events:
    games = event.get("competitions", [])
    if not games:
        continue
    sides = {c.get("homeAway"): c for c in games[0].get("competitors", [])}
    if "home" not in sides or "away" not in sides:
        continue
    home = sides["home"]["team"].get("abbreviation", "").upper()
    away = sides["away"]["team"].get("abbreviation", "").upper()
    if home not in ratings or away not in ratings:
        continue
    difference = ratings[home] - ratings[away]
    output.append({"UTC tipoff": event.get("date", ""), "Away": away, "Home": home,
                   "Away projected": round(114.5 - difference / 2, 2),
                   "Home projected": round(116.5 + difference / 2, 2),
                   "Status": event.get("status", {}).get("type", {}).get("name", "")})
with (data / "live_projections.csv").open("w", newline="") as f:
    columns = ["UTC tipoff", "Away", "Home", "Away projected", "Home projected", "Status"]
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    writer.writerows(output)
print("Generated projections:", len(output))
