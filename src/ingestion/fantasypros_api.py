"""FantasyPros v2 API client.

Auth: API key sent via the x-api-key header (loaded from .env, never hardcoded).
Base URL: https://api.fantasypros.com/public/v2/json

One call per position returns every player at that position for the season,
already including a "points_half" field — so a full draft-projection set for
all 6 positions costs 6 calls total, regardless of the account's daily limit.
Responses are cached to disk by (season, position) so repeated dev runs cost
zero additional calls.
"""

import json
import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.fantasypros.com/public/v2/json"
POSITIONS = ("QB", "RB", "WR", "TE", "K", "DST")
DEFAULT_CACHE_DIR = Path("data/raw/fantasypros_api")


def _headers():
    key = os.environ.get("FANTASYPROS_API_KEY")
    if not key:
        raise RuntimeError("FANTASYPROS_API_KEY not set in .env")
    return {"x-api-key": key}


def get_projections(season, position, week=None, scoring="HALF"):
    """Raw API call for one position. Returns the requests.Response."""
    url = f"{BASE_URL}/nfl/{season}/projections"
    params = {"position": position, "scoring": scoring}
    if week is not None:
        params["week"] = week
    return requests.get(url, headers=_headers(), params=params, timeout=15)


def fetch_all_projections(season, positions=POSITIONS, cache_dir=DEFAULT_CACHE_DIR, force_refresh=False):
    """Fetch (or load from cache) projections for every position and combine.

    Returns columns: player, position, team, proj_points
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    for pos in positions:
        cache_path = cache_dir / f"{season}_{pos}.json"
        if cache_path.exists() and not force_refresh:
            payload = json.loads(cache_path.read_text())
        else:
            resp = get_projections(season, pos)
            resp.raise_for_status()
            payload = resp.json()
            cache_path.write_text(json.dumps(payload))

        for p in payload["players"]:
            frames.append({
                "player": p["name"],
                "position": pos,
                "team": p["team_id"],
                "proj_points": p["stats"]["points_half"],
            })

    return pd.DataFrame(frames)
