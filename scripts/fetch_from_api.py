"""Download real matches once and save them as data/football_matches.csv.
Usage:  python scripts/fetch_from_api.py YOUR_API_KEY PL 2025"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import api_client

key, code, season = sys.argv[1], sys.argv[2], int(sys.argv[3])
clean, report = api_client.load_from_api(key, [code], season)
clean = clean[["match_id", "date", "competition", "home_team", "away_team", "home_score", "away_score"]]
clean.to_csv("data/football_matches.csv", index=False)
print(f"Saved {len(clean)} matches ({report.rows_removed} rows removed).")