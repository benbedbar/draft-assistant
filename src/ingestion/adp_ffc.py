"""ADP ingestion from the Fantasy Football Calculator public API (no key required).

Docs: https://fantasyfootballcalculator.com/api/v1
"""

import requests

BASE_URL = "https://fantasyfootballcalculator.com/api/v1/adp"


def fetch_adp(scoring="half-ppr", teams=10, year=None):
    """Fetch ADP for a given format/team count, optionally for a historical year.

    Returns a list of dicts: name, position, team, adp, adp_formatted, times_drafted, ...
    """
    url = f"{BASE_URL}/{scoring}"
    params = {"teams": teams}
    if year is not None:
        params["year"] = year
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    return payload["players"]
