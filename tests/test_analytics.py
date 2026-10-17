"""Tests for src/analytics.py. Run from the project folder:

    python -m unittest discover -s tests -v

The tiny dataset below was worked out by hand, so every expected number can be
checked on paper:

  M1  2025-01-01  League  A 2-0 B
  M2  2025-01-08  League  B 1-1 C
  M3  2025-01-15  League  C 0-3 A
  M4  2025-02-01  Cup     B 2-1 A
  M5  2025-02-10  Cup     C 1-0 B
"""

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import analytics, data_loader  # noqa: E402


def make_matches():
    raw = pd.DataFrame(
        {
            "match_id": ["M1", "M2", "M3", "M4", "M5"],
            "date": ["2025-01-01", "2025-01-08", "2025-01-15", "2025-02-01", "2025-02-10"],
            "competition": ["League", "League", "League", "Cup", "Cup"],
            "home_team": ["A", "B", "C", "B", "C"],
            "away_team": ["B", "C", "A", "A", "B"],
            "home_score": [2, 1, 0, 2, 1],
            "away_score": [0, 1, 3, 1, 0],
        }
    )
    clean, _ = data_loader.clean_matches(raw)
    return clean


class TeamStatsTests(unittest.TestCase):
    def setUp(self):
        self.matches = make_matches()
        self.stats = analytics.calculate_team_stats(self.matches).set_index("team")

    def test_wins_draws_losses(self):
        self.assertEqual(self.stats.loc["A", ["played", "wins", "draws", "losses"]].tolist(), [3, 2, 0, 1])
        self.assertEqual(self.stats.loc["B", ["played", "wins", "draws", "losses"]].tolist(), [4, 1, 1, 2])
        self.assertEqual(self.stats.loc["C", ["played", "wins", "draws", "losses"]].tolist(), [3, 1, 1, 1])

    def test_goals_and_goal_difference(self):
        self.assertEqual(self.stats.loc["A", ["goals_for", "goals_against", "goal_difference"]].tolist(), [6, 2, 4])
        self.assertEqual(self.stats.loc["B", ["goals_for", "goals_against", "goal_difference"]].tolist(), [3, 5, -2])
        self.assertEqual(self.stats.loc["C", ["goals_for", "goals_against", "goal_difference"]].tolist(), [2, 4, -2])

    def test_points(self):
        self.assertEqual(self.stats["points"].to_dict(), {"A": 6, "B": 4, "C": 4})

    def test_win_percentage(self):
        self.assertAlmostEqual(self.stats.loc["A", "win_pct"], 66.7, places=1)
        self.assertAlmostEqual(self.stats.loc["B", "win_pct"], 25.0, places=1)

    def test_every_match_gives_points_consistently(self):
        # Wins of all teams must equal losses of all teams (every non-draw has a winner and a loser).
        self.assertEqual(self.stats["wins"].sum(), self.stats["losses"].sum())
        self.assertEqual(self.stats["goals_for"].sum(), self.stats["goals_against"].sum())


class StandingsTests(unittest.TestCase):
    def test_order_uses_points_then_goal_difference_then_goals_scored(self):
        table = analytics.calculate_standings(make_matches())
        # B and C both have 4 points and goal difference -2; B scored 3 goals, C only 2.
        self.assertEqual(table["team"].tolist(), ["A", "B", "C"])
        self.assertEqual(table["position"].tolist(), [1, 2, 3])

    def test_goal_difference_breaks_a_points_tie(self):
        raw = pd.DataFrame(
            {
                "match_id": ["1", "2"],
                "date": ["2025-01-01", "2025-01-02"],
                "competition": ["L", "L"],
                "home_team": ["X", "Z"],
                "away_team": ["Y", "W"],
                "home_score": [5, 1],
                "away_score": [0, 0],
            }
        )
        clean, _ = data_loader.clean_matches(raw)
        table = analytics.calculate_standings(clean)
        # X and Z both have 3 points; X has goal difference +5, Z only +1.
        self.assertEqual(table["team"].tolist()[:2], ["X", "Z"])

    def test_empty_data_gives_empty_table(self):
        empty = make_matches().iloc[0:0]
        self.assertTrue(analytics.calculate_standings(empty).empty)
        self.assertTrue(analytics.calculate_team_stats(empty).empty)


class ComparisonTests(unittest.TestCase):
    def test_compare_two_teams(self):
        result = analytics.compare_teams(make_matches(), "A", "B")
        self.assertEqual(result["team"].tolist(), ["A", "B"])
        self.assertEqual(result["points"].tolist(), [6, 4])
        self.assertEqual(result["goal_difference"].tolist(), [4, -2])

    def test_team_without_matches_gets_zeros(self):
        result = analytics.compare_teams(make_matches(), "A", "Nobody")
        self.assertEqual(result.loc[1, "played"], 0)
        self.assertEqual(result.loc[1, "win_pct"], 0)

    def test_head_to_head(self):
        direct = analytics.head_to_head(make_matches(), "A", "B")
        self.assertEqual(direct["match_id"].tolist(), ["M1", "M4"])

    def test_comparison_table_text(self):
        table = analytics.comparison_table(analytics.compare_teams(make_matches(), "A", "B"))
        goal_diff = table[table["Metric"] == "Goal difference"].iloc[0]
        self.assertEqual(goal_diff["A"], "+4")
        self.assertEqual(goal_diff["B"], "-2")


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.matches = make_matches()

    def test_team_filter_matches_home_or_away(self):
        self.assertEqual(len(analytics.filter_matches(self.matches, teams=["A"])), 3)

    def test_date_filter_is_inclusive(self):
        out = analytics.filter_matches(self.matches, start_date="2025-01-08", end_date="2025-01-15")
        self.assertEqual(out["match_id"].tolist(), ["M2", "M3"])

    def test_competition_filter(self):
        self.assertEqual(len(analytics.filter_matches(self.matches, competitions=["Cup"])), 2)
        self.assertEqual(len(analytics.filter_matches(self.matches, competitions=[])), 0)

    def test_result_filter(self):
        out = analytics.filter_matches(self.matches, results=["Draw"])
        self.assertEqual(out["match_id"].tolist(), ["M2"])

    def test_search_text(self):
        out = analytics.filter_matches(self.matches, search_text=" cup ")
        self.assertEqual(len(out), 2)

    def test_filters_work_together(self):
        out = analytics.filter_matches(self.matches, teams=["B"], competitions=["League"], results=["Home Win"])
        # The team filter matches home OR away, so M1 (A 2-0 B, a League home win) is the only match left.
        self.assertEqual(out["match_id"].tolist(), ["M1"])

    def test_filtering_to_nothing_does_not_break_calculations(self):
        nothing = analytics.filter_matches(self.matches, teams=["A"], competitions=["Nowhere"])
        self.assertTrue(nothing.empty)
        self.assertEqual(analytics.summarise_matches(nothing)["total_matches"], 0)
        self.assertTrue(analytics.goals_per_match_by_month(nothing).empty)
        self.assertTrue(analytics.home_away_goals(nothing).empty)


class SummaryTests(unittest.TestCase):
    def test_dashboard_summary(self):
        summary = analytics.summarise_matches(make_matches())
        self.assertEqual(summary["total_matches"], 5)
        self.assertEqual(summary["total_teams"], 3)
        self.assertEqual(summary["total_goals"], 11)
        self.assertEqual(summary["avg_goals"], 2.2)
        self.assertEqual(summary["top_team"], "A")

    def test_goals_per_month(self):
        monthly = analytics.goals_per_match_by_month(make_matches())
        self.assertEqual(monthly["matches"].tolist(), [3, 2])
        self.assertEqual(monthly["total_goals"].tolist(), [2 + 2 + 3, 3 + 1])
        self.assertEqual(monthly["goals_per_match"].tolist(), [2.33, 2.0])

    def test_home_and_away_goals(self):
        table = analytics.home_away_goals(make_matches()).set_index("team")
        self.assertEqual(table.loc["A"].tolist(), [2, 4])
        self.assertEqual(table.loc["B"].tolist(), [3, 0])

    def test_recent_results_newest_first(self):
        self.assertEqual(analytics.recent_results(make_matches(), 2)["match_id"].tolist(), ["M5", "M4"])

    def test_safe_divide(self):
        self.assertEqual(analytics.safe_divide(5, 0), 0.0)
        self.assertEqual(analytics.safe_divide(5, 2), 2.5)


class DisplayAndCsvTests(unittest.TestCase):
    def test_match_table_is_exportable_to_csv(self):
        table = analytics.matches_for_display(make_matches())
        csv_text = table.to_csv(index=False)
        self.assertTrue(csv_text.startswith("Date,Competition,Home Team,Home Score,Away Score,Away Team,Result"))
        self.assertEqual(len(csv_text.strip().splitlines()), 6)  # header + 5 matches

    def test_standings_csv_has_all_columns(self):
        table = analytics.stats_for_display(analytics.calculate_standings(make_matches()))
        self.assertEqual(table.columns.tolist(), ["Pos", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"])


if __name__ == "__main__":
    unittest.main()
