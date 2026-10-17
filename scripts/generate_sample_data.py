"""Create data/football_matches.csv - a SYNTHETIC (made-up) sample dataset.

Run from the project folder:   python scripts/generate_sample_data.py

The teams are fictional and the scores are random numbers (a seeded Poisson
model), so the same file is produced every time. These are NOT real results.
To use real data, simply replace the CSV with your own file that has the same
columns (see README.md).
"""

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2025
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "football_matches.csv"

# team: (attack strength, defensive weakness). Higher attack = scores more;
# higher defensive weakness = concedes more.
TEAMS = {
    "Northbridge United": (1.35, 0.80),
    "Rivermouth Rovers": (1.25, 0.90),
    "Eastgate Athletic": (1.15, 0.95),
    "Harbour City FC": (1.10, 1.00),
    "Kingsfield Town": (1.05, 1.00),
    "Ashford Wanderers": (1.00, 1.05),
    "Westvale Albion": (0.95, 1.00),
    "Stonebridge Rangers": (0.90, 1.05),
    "Greenhill Borough": (0.85, 1.10),
    "Lakeside Orient": (0.85, 1.15),
    "Millbrook Victoria": (0.75, 1.15),
    "Oakwood Dynamo": (0.70, 1.25),
}


def round_robin(teams):
    """Every team plays every other team once (circle method). Returns a list of rounds."""
    order = list(teams)
    n = len(order)
    rounds = []
    for r in range(n - 1):
        pairs = []
        for i in range(n // 2):
            a, b = order[i], order[n - 1 - i]
            pairs.append((a, b) if (r + i) % 2 == 0 else (b, a))
        rounds.append(pairs)
        order = [order[0]] + [order[-1]] + order[1:-1]
    return rounds


def simulate_score(rng, home, away):
    home_attack, home_weak = TEAMS[home]
    away_attack, away_weak = TEAMS[away]
    home_goals = rng.poisson(1.30 * home_attack * away_weak * 1.10)
    away_goals = rng.poisson(1.15 * away_attack * home_weak * 0.95)
    return int(home_goals), int(away_goals)


def main():
    rng = np.random.default_rng(SEED)
    names = list(TEAMS)
    records = []

    # Premier Division: double round-robin, one round per Saturday from 17 Aug 2024.
    first_half = round_robin(names)
    second_half = [[(b, a) for a, b in pairs] for pairs in first_half]
    saturday = date(2024, 8, 17)
    for week, pairs in enumerate(first_half + second_half):
        for home, away in pairs:
            records.append(("Premier Division", saturday + timedelta(weeks=week), home, away))

    # Challenge Cup: 24 random pairings on Wednesdays (Sep 2024 - Apr 2025).
    wednesdays = [date(2024, 9, 4) + timedelta(weeks=k) for k in range(0, 32, 2)]
    for k in range(24):
        home, away = rng.choice(names, size=2, replace=False)
        records.append(("Challenge Cup", wednesdays[k % len(wednesdays)], str(home), str(away)))

    # Friendly Series: 12 pre-season friendlies in early August 2024.
    for k in range(12):
        home, away = rng.choice(names, size=2, replace=False)
        records.append(("Friendly Series", date(2024, 8, 3) + timedelta(days=k % 8), str(home), str(away)))

    df = pd.DataFrame(records, columns=["competition", "date", "home_team", "away_team"])
    scores = [simulate_score(rng, h, a) for h, a in zip(df["home_team"], df["away_team"])]
    df["home_score"] = [s[0] for s in scores]
    df["away_score"] = [s[1] for s in scores]

    df = df.sort_values(["date", "competition", "home_team"]).reset_index(drop=True)
    df.insert(0, "match_id", [f"M{i:04d}" for i in range(1, len(df) + 1)])
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    df = df[["match_id", "date", "competition", "home_team", "away_team", "home_score", "away_score"]]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(df)} synthetic matches to {OUTPUT}")


if __name__ == "__main__":
    main()
