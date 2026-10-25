"""Retrieve ESPN-reported NBA injuries. Missing/partial feed is never treated as healthy."""
from datetime import datetime,timezone
from pathlib import Path
try:
    from .feed_utils import fetch_json, write_rows, feed_status
except ImportError:
    from feed_utils import fetch_json, write_rows, feed_status

DATA=Path(__file__).resolve().parents[1]/"data"
URL="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
def main():
    try:
        payload=fetch_json(URL, array_key='injuries')
        return save_payload(payload)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        feed_status(DATA, 'injuries', error=exc)
        print(f'Injury feed unavailable; preserving previous snapshot: {exc}')
        return False

def save_payload(payload):
    if not isinstance(payload.get('injuries'), list) or not payload['injuries']:
        raise ValueError('Missing or empty injuries array; preserve previous snapshot')
    rows=[]
    for team in payload.get("injuries",[]):
        team_name=team.get("displayName") or team.get("team",{}).get("displayName","")
        if not team_name or not isinstance(team.get('injuries'), list):
            raise ValueError('Incomplete injury team record; preserve previous snapshot')
        for item in team['injuries']:
            athlete=item.get("athlete",{})
            rows.append({"team":team_name,"player":athlete.get("displayName",""),
                         "status":item.get("status",""),"details":str(item.get("details",""))[:500],
                         "captured_utc":datetime.now(timezone.utc).isoformat(),"source":"ESPN"})
    write_rows(DATA/'injuries.csv', ['team','player','status','details','captured_utc','source'], rows)
    feed_status(DATA, 'injuries', rows=len(rows))
    return True

if __name__=='__main__': main()
