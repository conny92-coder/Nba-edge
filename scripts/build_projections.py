"""Build today's projections; preserve the previous snapshot on feed failure."""
import csv
from datetime import datetime, timezone
from pathlib import Path

try:
    from .feed_utils import fetch_json, write_rows, feed_status
except ImportError:
    from feed_utils import fetch_json, write_rows, feed_status

DATA = Path(__file__).resolve().parents[1] / 'data'
FIELDS = ['UTC tipoff', 'Away', 'Home', 'Away projected', 'Home projected', 'Status']


def main(data=DATA):
    data = Path(data)
    try:
        with (data / 'power_ratings.csv').open() as f:
            ratings = {r['Code']: float(r['Live Net']) for r in csv.DictReader(f)}
        updated = data / 'updated_ratings.csv'
        if updated.exists():
            with updated.open() as f:
                ratings.update({r['Code']: float(r['Updated Net']) for r in csv.DictReader(f)})
        day = datetime.now(timezone.utc).strftime('%Y%m%d')
        payload = fetch_json('https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=' + day)
        output = []
        for event in payload['events']:
            competition = event['competitions'][0]
            sides = {c['homeAway']: c for c in competition['competitors']}
            home = sides['home']['team']['abbreviation'].upper()
            away = sides['away']['team']['abbreviation'].upper()
            # ESPN uses alternate abbreviations for these franchises.
            aliases = {'GS': 'GSW', 'NY': 'NYK', 'NO': 'NOP', 'SA': 'SAS', 'UTAH': 'UTA', 'WSH': 'WAS', 'PHO': 'PHX'}
            home, away = aliases.get(home, home), aliases.get(away, away)
            difference = ratings[home] - ratings[away]
            output.append({'UTC tipoff': event['date'], 'Away': away, 'Home': home,
                           'Away projected': round(114.5 - difference / 2, 2),
                           'Home projected': round(116.5 + difference / 2, 2),
                           'Status': event.get('status', {}).get('type', {}).get('name', '')})
        write_rows(data / 'live_projections.csv', FIELDS, output)
        feed_status(data, 'projections', rows=len(output))
        print('Generated projections:', len(output))
        return True
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        feed_status(data, 'projections', error=exc)
        print(f'Projection refresh unavailable; preserving previous snapshot: {exc}')
        return False


if __name__ == '__main__':
    main()
