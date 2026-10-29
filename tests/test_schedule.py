import unittest
from datetime import datetime, timezone
from scripts.build_projections import eastern_day, project_events

class ScheduleTests(unittest.TestCase):
    def test_utc_after_midnight_still_previous_eastern_day(self):
        self.assertEqual(eastern_day(datetime(2026, 10, 30, 1, 30, tzinfo=timezone.utc)), "20261029")

    def test_late_night_tipoff_is_included_on_eastern_day(self):
        event = {"date": "2026-10-30T01:30Z",
                 "status": {"type": {"name": "STATUS_SCHEDULED"}},
                 "competitions": [{"competitors": [
                     {"homeAway": "home", "team": {"abbreviation": "BOS"}},
                     {"homeAway": "away", "team": {"abbreviation": "NYK"}}
                 ]}]}
        rows = project_events([event], {"BOS": 5.0, "NYK": 3.0}, "20261029")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Home"], "BOS")
        self.assertEqual(project_events([event], {"BOS": 5.0, "NYK": 3.0}, "20261030"), [])

if __name__ == "__main__":
    unittest.main()
