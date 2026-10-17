"""Load, validate and clean the football match CSV file.

Everything in this file is about getting *trustworthy* data into the app.
After `load_matches()` runs, the rest of the app can assume that:
  * all required columns exist,
  * dates are real dates and scores are whole numbers >= 0,
  * team and competition names have no stray spaces,
  * every row has a unique match_id.
Rows that break these rules are removed and counted in a CleaningReport,
so the app can tell the user exactly what happened.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

# The columns every dataset must contain (extra columns are allowed and ignored).
REQUIRED_COLUMNS = [
    "match_id",
    "date",
    "competition",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
]
TEXT_COLUMNS = ["competition", "home_team", "away_team"]

# Text labels used in the "result" column.
RESULT_HOME_WIN = "Home Win"
RESULT_DRAW = "Draw"
RESULT_AWAY_WIN = "Away Win"
RESULT_OPTIONS = [RESULT_HOME_WIN, RESULT_DRAW, RESULT_AWAY_WIN]


class DataValidationError(Exception):
    """Raised when the dataset cannot be used at all (missing file, missing columns...)."""


@dataclass
class CleaningReport:
    """A summary of what the cleaning step did."""

    rows_read: int = 0
    rows_kept: int = 0
    problems: dict = field(default_factory=dict)  # {"reason": number_of_rows}

    @property
    def rows_removed(self) -> int:
        return self.rows_read - self.rows_kept


def check_required_columns(df: pd.DataFrame) -> None:
    """Stop with a clear message if any required column is missing."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise DataValidationError(
            "The data is missing required column(s): "
            + ", ".join(missing)
            + ". The CSV must contain: "
            + ", ".join(REQUIRED_COLUMNS)
            + "."
        )


def add_result_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'result' column: Home Win, Draw or Away Win."""
    out = df.copy()
    out["result"] = np.where(
        out["home_score"] > out["away_score"],
        RESULT_HOME_WIN,
        np.where(out["home_score"] == out["away_score"], RESULT_DRAW, RESULT_AWAY_WIN),
    )
    return out


def _as_bool(mask: pd.Series) -> pd.Series:
    """Turn a True/False/missing mask into a plain True/False mask."""
    return mask.fillna(False).astype(bool)


def clean_matches(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Validate and clean a raw DataFrame. Returns (clean_dataframe, report)."""
    check_required_columns(raw)
    report = CleaningReport(rows_read=len(raw))
    work = raw[REQUIRED_COLUMNS].copy()

    # 1. Convert every column to the type we expect. Bad values become NaN/NaT.
    for col in TEXT_COLUMNS:
        work[col] = work[col].astype("string").str.strip()
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work["home_score"] = pd.to_numeric(work["home_score"], errors="coerce")
    work["away_score"] = pd.to_numeric(work["away_score"], errors="coerce")

    # 2. Build one True/False mask per problem (True = this row has the problem).
    missing_text = _as_bool(work[TEXT_COLUMNS].isna().any(axis=1)) | _as_bool(
        (work[TEXT_COLUMNS] == "").any(axis=1)
    )
    same_team = _as_bool(work["home_team"] == work["away_team"])
    missing_score = work["home_score"].isna() | work["away_score"].isna()
    bad_score = (
        (work["home_score"] < 0)
        | (work["away_score"] < 0)
        | (work["home_score"] % 1 != 0)
        | (work["away_score"] % 1 != 0)
    )

    checks = [
        ("Missing or invalid date", work["date"].isna()),
        ("Missing match_id", work["match_id"].isna()),
        ("Missing team or competition name", missing_text),
        ("Home and away team are the same", same_team),
        ("Missing or non-numeric score", missing_score),
        ("Negative or non-whole-number score", bad_score),
        ("Duplicate match_id", work["match_id"].duplicated(keep="first")),
    ]

    # 3. A row is counted under the FIRST problem it has, so the numbers add up.
    rejected = pd.Series(False, index=work.index)
    for reason, mask in checks:
        newly_rejected = _as_bool(mask) & ~rejected
        count = int(newly_rejected.sum())
        if count > 0:
            report.problems[reason] = count
        rejected = rejected | newly_rejected

    # 4. Keep only good rows and finish the preparation.
    clean = work.loc[~rejected].copy()
    clean["match_id"] = clean["match_id"].astype(str)
    clean["home_score"] = clean["home_score"].astype(int)
    clean["away_score"] = clean["away_score"].astype(int)
    clean["date"] = clean["date"].dt.normalize()
    for col in TEXT_COLUMNS:
        clean[col] = clean[col].astype(str)

    clean = add_result_column(clean)
    clean["total_goals"] = clean["home_score"] + clean["away_score"]
    clean = clean.sort_values(["date", "match_id"]).reset_index(drop=True)

    report.rows_kept = len(clean)
    return clean, report


def load_matches(path) -> tuple[pd.DataFrame, CleaningReport]:
    """Read the CSV file at `path`, then validate and clean it."""
    path = Path(path)
    if not path.exists():
        raise DataValidationError(
            f"Could not find the data file: {path}. "
            "Check that data/football_matches.csv is in your project folder."
        )
    try:
        raw = pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise DataValidationError("The CSV file is empty (it has no header row).") from exc
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise DataValidationError(f"The CSV file could not be read: {exc}") from exc
    return clean_matches(raw)
