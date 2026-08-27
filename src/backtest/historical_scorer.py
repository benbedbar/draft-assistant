"""Real historical outcomes for the Part 6 backtest -- actual games that were
actually played, not projections and not simulated variance.

K and DST have no player-level nflverse history (same gap noted in
src/ingestion/nflverse_historical.py and src/simulation/season_scorer.py), so
there's no real-outcomes source for them at all here. Rather than fabricate
"actual" K/DST performance, the backtest excludes K/DST from scoring
entirely -- symmetrically for me and every opponent, so the comparison stays
apples-to-apples. They're still drafted (roster construction is unchanged),
just not counted.
"""

import numpy as np
import pandas as pd

from config.league_settings import NUM_WEEKS
from src.ingestion.nflverse_historical import fetch_weekly_skill_position_data


def build_actual_weekly_points(season):
    """Return {player_display_name: np.ndarray of length NUM_WEEKS} of real half-PPR points.

    Weeks the player didn't appear in (bye, injury, not yet on a roster) are 0,
    matching what actually happened -- no imputation.
    """
    weekly = fetch_weekly_skill_position_data([season])
    pivot = weekly.pivot_table(
        index="player_display_name", columns="week", values="half_ppr_points", aggfunc="sum", fill_value=0.0
    )
    actual = {}
    for name, row in pivot.iterrows():
        arr = np.zeros(NUM_WEEKS)
        for week, points in row.items():
            if 1 <= week <= NUM_WEEKS:
                arr[week - 1] = points
        actual[name] = arr
    return actual
