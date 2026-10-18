"""Fetch matches from football-data.org (v4) and convert them to the app's format."""

import pandas as pd
import requests

from src import data_loader

BASE_URL = "https://api.football-data.org/v4"
COLUMNS = ["match_id", "date", "competition", "home_team", "away_team",
           "home_score", "away_score", "status"]


class ApiError(Exception):
    """Raised with a readable message when the API call fails."""


def _get(api_key, path, params=None, timeout=15):
    try:
        response = requests.get(
            BASE_URL + path,
            headers={"X-Auth-Token": api_key},
            params=params or {},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise ApiError(f"Could not reach the football API: {exc}") from exc

    if response.status_code == 401 or response.status_code == 403:
        raise ApiError("The API refused the request. Check your key, or this "
                       "competition/season may not be included in your plan.")
    if response.status_code == 404:
        raise ApiError("The API could not find that competition or season.")
    if response.status_code == 429:
        raise ApiError("Too many requests (free plan: about 10 per minute). "
                       "Wait a minute and try again.")
    if response.status_code != 200:
        raise ApiError(f"The API returned an error (HTTP {response.status_code}).")
    return response.json()


def _to_dataframe(matches):
    rows = []
    for m in matches:
        full_time = (m.get("score") or {}).get("fullTime") or {}
        rows.append({
            "match_id": m.get("id"),
            "date": (m.get("utcDate") or "")[:10],
            "competition": (m.get("competition") or {}).get("name"),
            "home_team": (m.get("homeTeam") or {}).get("name"),
            "away_team": (m.get("awayTeam") or {}).get("name"),
            "home_score": full_time.get("home"),
            "away_score": full_time.get("away"),
            "status": m.get("status"),
        })
    return pd.DataFrame(rows, columns=COLUMNS)


def fetch_competition_matches(api_key, competition_code, season=None):
    """All matches of one competition, e.g. code 'PL' = Premier League."""
    params = {"season": season} if season else {}
    data = _get(api_key, f"/competitions/{competition_code}/matches", params)
    return _to_dataframe(data.get("matches", []))


def load_from_api(api_key, competition_codes, season=None):
    """Fetch finished matches for several competitions, then clean them
    with the same validation used for the CSV file."""
    if not api_key:
        raise ApiError("No API key found. Add FOOTBALL_DATA_API_KEY to your secrets.")
    frames = [fetch_competition_matches(api_key, code, season) for code in competition_codes]
    raw = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS)
    raw = raw[raw["status"] == "FINISHED"].drop(columns="status")
    return data_loader.clean_matches(raw)


def fetch_live_matches(api_key):
    """Matches in play right now (free plan: delayed)."""
    data = _get(api_key, "/matches", {"status": "IN_PLAY,PAUSED"})
    return _to_dataframe(data.get("matches", [])).drop(columns="status")