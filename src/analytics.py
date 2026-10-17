"""All football calculations live here (no Streamlit code, so it is easy to test).

Main idea: the CSV has ONE row per match, but team statistics need ONE row per
team per match. `build_team_rows()` converts between the two, and every
statistic (wins, goals, points...) is then a simple group-and-sum.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

POINTS_WIN = 3
POINTS_DRAW = 1
POINTS_LOSS = 0

TEAM_STAT_COLUMNS = [
    "team",
    "played",
    "wins",
    "draws",
    "losses",
    "goals_for",
    "goals_against",
    "goal_difference",
    "points",
    "win_pct",
]

STANDINGS_COLUMNS = [
    "position",
    "team",
    "played",
    "wins",
    "draws",
    "losses",
    "goals_for",
    "goals_against",
    "goal_difference",
    "points",
]

# Friendly column names shown in tables and CSV downloads.
MATCH_LABELS = {
    "date": "Date",
    "competition": "Competition",
    "home_team": "Home Team",
    "home_score": "Home Score",
    "away_score": "Away Score",
    "away_team": "Away Team",
    "result": "Result",
}
STAT_LABELS = {
    "position": "Pos",
    "team": "Team",
    "played": "P",
    "wins": "W",
    "draws": "D",
    "losses": "L",
    "goals_for": "GF",
    "goals_against": "GA",
    "goal_difference": "GD",
    "points": "Pts",
    "win_pct": "Win %",
}


def safe_divide(numerator, denominator) -> float:
    """Divide two numbers, returning 0.0 instead of crashing when denominator is 0."""
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


# --------------------------------------------------------------------------
# Filtering
# --------------------------------------------------------------------------
def filter_matches(
    df: pd.DataFrame,
    teams=None,
    competitions=None,
    start_date=None,
    end_date=None,
    results=None,
    search_text: str = "",
) -> pd.DataFrame:
    """Return only the matches that satisfy every filter that was given.

    * teams:        keep matches where the home OR away team is in the list
    * competitions: keep matches in these competitions (an empty list = no matches)
    * start_date / end_date: inclusive date range
    * results:      list of "Home Win" / "Draw" / "Away Win"
    * search_text:  text typed in the search box (team or competition name)
    A filter set to None (or empty, for teams/results) is simply skipped.
    """
    out = df
    if teams:
        out = out[out["home_team"].isin(teams) | out["away_team"].isin(teams)]
    if competitions is not None:
        out = out[out["competition"].isin(competitions)]
    if start_date is not None:
        out = out[out["date"] >= pd.Timestamp(start_date)]
    if end_date is not None:
        out = out[out["date"] <= pd.Timestamp(end_date)]
    if results:
        out = out[out["result"].isin(results)]
    needle = (search_text or "").strip().lower()
    if needle:
        found = (
            out["home_team"].str.lower().str.contains(needle, regex=False)
            | out["away_team"].str.lower().str.contains(needle, regex=False)
            | out["competition"].str.lower().str.contains(needle, regex=False)
        )
        out = out[found]
    return out.copy()


# --------------------------------------------------------------------------
# Team statistics
# --------------------------------------------------------------------------
def build_team_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Turn 'one row per match' into 'one row per team per match'."""
    home = pd.DataFrame(
        {
            "team": df["home_team"],
            "opponent": df["away_team"],
            "goals_for": df["home_score"],
            "goals_against": df["away_score"],
        }
    )
    away = pd.DataFrame(
        {
            "team": df["away_team"],
            "opponent": df["home_team"],
            "goals_for": df["away_score"],
            "goals_against": df["home_score"],
        }
    )
    rows = pd.concat([home, away], ignore_index=True)
    rows["outcome"] = np.where(
        rows["goals_for"] > rows["goals_against"],
        "W",
        np.where(rows["goals_for"] == rows["goals_against"], "D", "L"),
    )
    rows["points"] = rows["outcome"].map({"W": POINTS_WIN, "D": POINTS_DRAW, "L": POINTS_LOSS})
    rows["win"] = (rows["outcome"] == "W").astype(int)
    rows["draw"] = (rows["outcome"] == "D").astype(int)
    rows["loss"] = (rows["outcome"] == "L").astype(int)
    return rows


def calculate_team_stats(df: pd.DataFrame) -> pd.DataFrame:
    """One row per team: played, W/D/L, goals, goal difference, points, win %."""
    if df.empty:
        return pd.DataFrame(columns=TEAM_STAT_COLUMNS)

    rows = build_team_rows(df)
    stats = rows.groupby("team").agg(
        played=("outcome", "size"),
        wins=("win", "sum"),
        draws=("draw", "sum"),
        losses=("loss", "sum"),
        goals_for=("goals_for", "sum"),
        goals_against=("goals_against", "sum"),
        points=("points", "sum"),
    )
    stats["goal_difference"] = stats["goals_for"] - stats["goals_against"]
    # played is never 0 here (a team only appears if it played), but we stay safe anyway.
    stats["win_pct"] = (
        (stats["wins"] / stats["played"].where(stats["played"] > 0)).fillna(0.0) * 100
    ).round(1)
    stats = stats.reset_index()
    return stats[TEAM_STAT_COLUMNS]


def calculate_standings(df: pd.DataFrame) -> pd.DataFrame:
    """League table: sorted by points, then goal difference, then goals scored."""
    stats = calculate_team_stats(df)
    if stats.empty:
        return pd.DataFrame(columns=STANDINGS_COLUMNS)
    # Team name is the final tie-breaker only so the order is always the same.
    table = stats.sort_values(
        by=["points", "goal_difference", "goals_for", "team"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    table.insert(0, "position", range(1, len(table) + 1))
    return table[STANDINGS_COLUMNS]


def compare_teams(df: pd.DataFrame, team_a: str, team_b: str) -> pd.DataFrame:
    """Two-row table of statistics for the chosen teams (zeros if a team has no matches)."""
    stats = calculate_team_stats(df).set_index("team")
    records = []
    for team in (team_a, team_b):
        if team in stats.index:
            record = stats.loc[team].to_dict()
        else:
            record = {col: 0 for col in TEAM_STAT_COLUMNS if col != "team"}
        record["team"] = team
        records.append(record)
    return pd.DataFrame(records)[TEAM_STAT_COLUMNS]


def comparison_table(comparison: pd.DataFrame) -> pd.DataFrame:
    """Side-by-side table (one row per metric, one column per team) made of text."""
    metrics = [
        ("played", "Matches played"),
        ("wins", "Wins"),
        ("draws", "Draws"),
        ("losses", "Losses"),
        ("goals_for", "Goals scored"),
        ("goals_against", "Goals conceded"),
        ("goal_difference", "Goal difference"),
        ("points", "Points"),
        ("win_pct", "Win percentage"),
    ]
    teams = comparison["team"].tolist()
    table_rows = []
    for column, label in metrics:
        row = {"Metric": label}
        for team, value in zip(teams, comparison[column].tolist()):
            if column == "win_pct":
                row[team] = f"{value:.1f}%"
            elif column == "goal_difference":
                row[team] = f"{int(value):+d}"
            else:
                row[team] = str(int(value))
        table_rows.append(row)
    return pd.DataFrame(table_rows)


def head_to_head(df: pd.DataFrame, team_a: str, team_b: str) -> pd.DataFrame:
    """All matches played directly between the two teams."""
    mask = ((df["home_team"] == team_a) & (df["away_team"] == team_b)) | (
        (df["home_team"] == team_b) & (df["away_team"] == team_a)
    )
    return df[mask].copy()


def home_away_goals(df: pd.DataFrame) -> pd.DataFrame:
    """Goals each team scored at home and away."""
    home = df.groupby("home_team")["home_score"].sum().rename("home_goals")
    away = df.groupby("away_team")["away_score"].sum().rename("away_goals")
    out = pd.concat([home, away], axis=1).fillna(0).astype(int)
    out.index.name = "team"
    return out.reset_index()


# --------------------------------------------------------------------------
# Dashboard helpers
# --------------------------------------------------------------------------
def summarise_matches(df: pd.DataFrame) -> dict:
    """Headline numbers for the dashboard cards."""
    if df.empty:
        return {
            "total_matches": 0,
            "total_teams": 0,
            "total_goals": 0,
            "avg_goals": 0.0,
            "top_team": "N/A",
            "top_team_points": 0,
        }
    teams = pd.unique(pd.concat([df["home_team"], df["away_team"]]))
    total_goals = int(df["home_score"].sum() + df["away_score"].sum())
    standings = calculate_standings(df)
    top = standings.iloc[0]
    return {
        "total_matches": int(len(df)),
        "total_teams": int(len(teams)),
        "total_goals": total_goals,
        "avg_goals": round(safe_divide(total_goals, len(df)), 2),
        "top_team": str(top["team"]),
        "top_team_points": int(top["points"]),
    }


def goals_per_match_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """Average goals per match for every calendar month."""
    if df.empty:
        return pd.DataFrame(columns=["month", "matches", "total_goals", "goals_per_match"])
    tmp = pd.DataFrame(
        {
            "month": df["date"].dt.to_period("M").dt.to_timestamp(),
            "total_goals": df["home_score"] + df["away_score"],
        }
    )
    monthly = tmp.groupby("month").agg(
        matches=("total_goals", "size"), total_goals=("total_goals", "sum")
    )
    monthly["goals_per_match"] = (monthly["total_goals"] / monthly["matches"]).round(2)
    return monthly.reset_index()


def recent_results(df: pd.DataFrame, count: int = 10) -> pd.DataFrame:
    """The latest `count` matches, newest first."""
    return df.sort_values(["date", "match_id"], ascending=False).head(count)


# --------------------------------------------------------------------------
# Display / download formatting (the same tables are used for CSV downloads)
# --------------------------------------------------------------------------
def matches_for_display(df: pd.DataFrame) -> pd.DataFrame:
    out = df[list(MATCH_LABELS)].copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    return out.rename(columns=MATCH_LABELS).reset_index(drop=True)


def stats_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Rename the columns of a standings or team-stats table to short labels."""
    return df.rename(columns=STAT_LABELS).reset_index(drop=True)
