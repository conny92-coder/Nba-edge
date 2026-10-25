import csv
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from scripts import build_projections as projections, daily_update, injury_check, feed_utils

ROOT = Path(__file__).resolve().parents[1]


def event(home='NY', away='GS'):
    return {'id': '1', 'date': '2026-10-25T23:00Z',
            'status': {'type': {'completed': True}},
            'competitions': [{'competitors': [
                {'homeAway': 'home', 'team': {'abbreviation': home}, 'score': '110'},
                {'homeAway': 'away', 'team': {'abbreviation': away}, 'score': '100'}]}]}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name)
        (self.data / 'power_ratings.csv').write_bytes((ROOT / 'data/power_ratings.csv').read_bytes())

    def test_all_teams(self):
        with (self.data / 'power_ratings.csv').open() as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 30)
        self.assertEqual({r['Code'] for r in rows}, daily_update.TEAMS)

    def test_projection_fallback_aliases_and_empty_day(self):
        with patch.object(projections, 'fetch_json', return_value={'events': [event()]}):
            self.assertTrue(projections.main(self.data))
        with (self.data / 'live_projections.csv').open() as f:
            rows = list(csv.DictReader(f))
        self.assertEqual((rows[0]['Home'], rows[0]['Away']), ('NYK', 'GSW'))
        before = (self.data / 'live_projections.csv').read_bytes()
        for payload in [{}, {'events': [{'competitions': []}]}]:
            with patch.object(projections, 'fetch_json', return_value=payload):
                self.assertFalse(projections.main(self.data))
            self.assertEqual(before, (self.data / 'live_projections.csv').read_bytes())
        with patch.object(projections, 'fetch_json', side_effect=urllib.error.URLError('offline')):
            self.assertFalse(projections.main(self.data))
        self.assertEqual(before, (self.data / 'live_projections.csv').read_bytes())
        self.assertTrue(json.loads((self.data / 'projections_status.json').read_text())['errors'])
        with patch.object(projections, 'fetch_json', return_value={'events': []}):
            self.assertTrue(projections.main(self.data))
        with (self.data / 'live_projections.csv').open() as f:
            self.assertEqual(list(csv.DictReader(f)), [])

    def test_results_replay_and_deduplication(self):
        with patch.object(daily_update, 'DATA', self.data), patch.object(daily_update, 'fetch_json', return_value={'events': [event()]}):
            self.assertTrue(daily_update.main())
            before = (self.data / 'updated_ratings.csv').read_bytes()
            self.assertTrue(daily_update.main())
        self.assertEqual(before, (self.data / 'updated_ratings.csv').read_bytes())
        with (self.data / 'updated_ratings.csv').open() as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 30)
        self.assertEqual(sum(int(r['Recorded Games']) for r in rows), 2)
        with patch.object(daily_update, 'DATA', self.data), patch.object(daily_update, 'fetch_json', side_effect=urllib.error.URLError('offline')):
            self.assertFalse(daily_update.main())
        self.assertEqual(before, (self.data / 'updated_ratings.csv').read_bytes())

    def test_injury_failure_preserves_snapshot(self):
        path = self.data / 'injuries.csv'
        path.write_text('previous snapshot')
        with patch.object(injury_check, 'DATA', self.data), patch.object(injury_check, 'fetch_json', return_value={'injuries': []}):
            self.assertFalse(injury_check.main())
        self.assertEqual(path.read_text(), 'previous snapshot')

    def test_feed_validation_and_retries(self):
        from io import BytesIO
        with patch.object(feed_utils.urllib.request, 'urlopen', return_value=BytesIO(b'{}')):
            with self.assertRaises(ValueError):
                feed_utils.fetch_json('https://example.com')
        with patch.object(feed_utils.urllib.request, 'urlopen', side_effect=[urllib.error.URLError('temporary'), BytesIO(b'{"events": []}')]) as request, patch.object(feed_utils.time, 'sleep'):
            self.assertEqual(feed_utils.fetch_json('https://example.com'), {'events': []})
            self.assertEqual(request.call_count, 2)


if __name__ == '__main__':
    unittest.main()
