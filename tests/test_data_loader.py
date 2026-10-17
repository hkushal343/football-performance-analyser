"""Tests for src/data_loader.py (validation, cleaning, error handling)."""

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import data_loader  # noqa: E402


def good_row(**changes):
    row = {
        "match_id": "M1",
        "date": "2025-01-01",
        "competition": "League",
        "home_team": "A",
        "away_team": "B",
        "home_score": 2,
        "away_score": 1,
    }
    row.update(changes)
    return row


class CleaningTests(unittest.TestCase):
    def test_valid_row_is_kept_and_result_is_added(self):
        clean, report = data_loader.clean_matches(pd.DataFrame([good_row()]))
        self.assertEqual(len(clean), 1)
        self.assertEqual(clean.loc[0, "result"], "Home Win")
        self.assertEqual(clean.loc[0, "total_goals"], 3)
        self.assertEqual(report.rows_removed, 0)

    def test_results_draw_and_away_win(self):
        rows = [
            good_row(match_id="1", home_score=1, away_score=1),
            good_row(match_id="2", home_score=0, away_score=2),
        ]
        clean, _ = data_loader.clean_matches(pd.DataFrame(rows))
        self.assertEqual(clean["result"].tolist(), ["Draw", "Away Win"])

    def test_invalid_rows_are_removed_and_counted(self):
        rows = [
            good_row(match_id="ok"),
            good_row(match_id="bad_date", date="not a date"),
            good_row(match_id="no_date", date=None),
            good_row(match_id="neg", home_score=-1),
            good_row(match_id="text_score", home_score="abc"),
            good_row(match_id="missing_score", away_score=None),
            good_row(match_id="decimal", home_score=1.5),
            good_row(match_id="same", home_team="A", away_team="A"),
            good_row(match_id="blank_team", home_team="   "),
            good_row(match_id="ok"),  # duplicate id
        ]
        clean, report = data_loader.clean_matches(pd.DataFrame(rows))
        self.assertEqual(clean["match_id"].tolist(), ["ok"])
        self.assertEqual(report.rows_read, 10)
        self.assertEqual(report.rows_kept, 1)
        self.assertEqual(report.rows_removed, 9)
        self.assertEqual(sum(report.problems.values()), 9)
        self.assertEqual(report.problems["Missing or invalid date"], 2)
        self.assertEqual(report.problems["Duplicate match_id"], 1)

    def test_text_is_trimmed(self):
        clean, _ = data_loader.clean_matches(pd.DataFrame([good_row(home_team="  A  ")]))
        self.assertEqual(clean.loc[0, "home_team"], "A")

    def test_scores_become_whole_numbers(self):
        clean, _ = data_loader.clean_matches(pd.DataFrame([good_row(home_score="3", away_score=2.0)]))
        self.assertEqual(clean.loc[0, "home_score"], 3)
        self.assertEqual(clean.loc[0, "away_score"], 2)

    def test_missing_required_column_raises_clear_error(self):
        raw = pd.DataFrame([good_row()]).drop(columns=["away_score"])
        with self.assertRaises(data_loader.DataValidationError) as context:
            data_loader.clean_matches(raw)
        self.assertIn("away_score", str(context.exception))

    def test_header_only_dataset_gives_empty_result(self):
        raw = pd.DataFrame(columns=data_loader.REQUIRED_COLUMNS)
        clean, report = data_loader.clean_matches(raw)
        self.assertTrue(clean.empty)
        self.assertEqual(report.rows_read, 0)

    def test_all_rows_invalid_gives_empty_result(self):
        clean, report = data_loader.clean_matches(pd.DataFrame([good_row(date="nope")]))
        self.assertTrue(clean.empty)
        self.assertEqual(report.rows_removed, 1)


class FileLoadingTests(unittest.TestCase):
    def test_missing_file(self):
        with self.assertRaises(data_loader.DataValidationError):
            data_loader.load_matches(ROOT / "data" / "does_not_exist.csv")

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "empty.csv"
            path.write_text("")
            with self.assertRaises(data_loader.DataValidationError):
                data_loader.load_matches(path)

    def test_sample_dataset_meets_project_requirements(self):
        clean, report = data_loader.load_matches(ROOT / "data" / "football_matches.csv")
        teams = set(clean["home_team"]) | set(clean["away_team"])
        self.assertGreaterEqual(len(clean), 100)
        self.assertGreaterEqual(len(teams), 10)
        self.assertGreaterEqual(clean["competition"].nunique(), 2)
        self.assertEqual(report.rows_removed, 0)
        self.assertTrue(clean["match_id"].is_unique)


if __name__ == "__main__":
    unittest.main()
