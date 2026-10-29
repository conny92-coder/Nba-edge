"""Generate provisional matchup projections for the NBA's Eastern-local calendar day."""
import csv
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

DATA = Path(__file__).resolve().parents[1] / "data"
EASTERN = ZoneInfo("America/New_York")
COLUMNS = ["UTC tipoff", "Away", "Home", "Away projected", "Home projected", "Status"]
URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates="

def eastern_day(now=None):
    instant = now or datetime.now(timezone.utc)
    return instant.astimezone(EASTERN).strftime("%Y%m%d")

def ratings_for_day(data_dir=DATA):
    with (data_dir / "power_ratings.csv").open(newline="", encoding="utf-8") as file:
        ratings = {row["Code"]: float(row["Live Net"]) for row in csv.DictReader(file)}
    updated = data_dir / "updated_ratings.csv"
    if updated.exists():
        with updated.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                if row["Code"] in ratings and row.get("Updated Net"):
                    ratings[row["Code"]] = float(row["Updated Net"])
    return ratings

def project_events(events, ratings, target_day):
    output = []
    for event in events:
        competitions = event.get("competitions") or []
        if not competitions:
            continue
        sides = {c.get("homeAway"): c for c in competitions[0].get("competitors", [])}
        if not all(side in sides for side in ("home", "away")):
            continue
        home = sides["home"].get("team", {}).get("abbreviation", "").upper()
        away = sides["away"].get("team", {}).get("abbreviation", "").upper()
        if home not in ratings or away not in ratings:
            continue
        tipoff = event.get("date", "")
        try:
            local_day = datetime.fromisoformat(tipoff.replace("Z", "+00:00")).astimezone(EASTERN).strftime("%Y%m%d")
        except (ValueError, TypeError):
            continue
        if local_day != target_day:
            continue
        difference = ratings[home] - ratings[away]
        output.append({"UTC tipoff": tipoff, "Away": away, "Home": home,
                       "Away projected": round(114.5 - difference / 2, 2),
                       "Home projected": round(116.5 + difference / 2, 2),
                       "Status": event.get("status", {}).get("type", {}).get("name", "")})
    return output

def main():
    day = eastern_day()
    request = urllib.request.Request(URL + day, headers={"User-Agent": "NBAEdgeResearch/1.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        events = json.load(response).get("events", [])
    rows = project_events(events, ratings_for_day(), day)
    path = DATA / "live_projections.csv"
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print("Eastern date:", day, "Generated projections:", len(rows))

if __name__ == "__main__":
    main()
