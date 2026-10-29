import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import daily_update

class ScoreboardTests(unittest.TestCase):
    def test_collect_completed_game_only(self):
        event = {
            "id": "fixture-1", "date": "2026-10-29T23:00Z",
            "status": {"type": {"completed": True}},
            "competitions": [{"competitors": [
                {"homeAway": "home", "score": "120", "team": {"abbreviation": "BOS"}},
                {"homeAway": "away", "score": "111", "team": {"abbreviation": "NYK"}}
            ]}]
        }
        scheduled = dict(event, id="fixture-2", status={"type": {"completed": False}})
        with patch.object(daily_update, "fetch_json", return_value={"events": [event, scheduled]}):
            rows = daily_update.collect("20261029")
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["home"], rows[0]["away"]), ("BOS", "NYK"))
        self.assertEqual((rows[0]["home_score"], rows[0]["away_score"]), (120, 111))

    def test_partial_source_outage_retains_previous_results_and_reports_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "power_ratings.csv").write_text(
                "Code,Team,Live Net\nBOS,Boston Celtics,5\nNYK,New York Knicks,3\n",
                encoding="utf-8"
            )
            (root / "game_results.csv").write_text(
                "game_id,date_utc,away,home,away_score,home_score,source\n"
                "old-1,2026-10-20T23:00Z,NYK,BOS,100,105,ESPN scoreboard\n",
                encoding="utf-8"
            )
            with patch.object(daily_update, "DATA", root), patch.object(
                daily_update, "collect", side_effect=ValueError("Invalid JSON")
            ):
                daily_update.main()
            with (root / "game_results.csv").open(newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["game_id"], "old-1")
            status = json.loads((root / "refresh_status.json").read_text(encoding="utf-8"))
            self.assertEqual(len(status["errors"]), 4)
            self.assertEqual(status["completed_games"], 1)

if __name__ == "__main__":
    unittest.main()
