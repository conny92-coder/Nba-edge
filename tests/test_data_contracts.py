import csv
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"ATL","BOS","BKN","CHA","CHI","CLE","DAL","DEN","DET","GSW","HOU","IND","LAC","LAL","MEM","MIA","MIL","MIN","NOP","NYK","OKC","ORL","PHI","PHX","POR","SAC","SAS","TOR","UTA","WAS"}

class DataContractTests(unittest.TestCase):
    def test_baseline_contains_all_thirty_teams(self):
        with (ROOT / "data" / "power_ratings.csv").open(newline="", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
        codes = [row["Code"] for row in rows]
        self.assertEqual(len(codes), 30)
        self.assertEqual(set(codes), EXPECTED)
        self.assertEqual(len(set(codes)), len(codes))
        for row in rows:
            self.assertTrue(-100 < float(row["Live Net"]) < 100)

if __name__ == "__main__":
    unittest.main()
