"""Part 6 backtest player pool: a given historical season's real ADP, merged
with that season's REAL actual weekly outcomes (not projections).

Ranking within a policy's positional constraint uses ADP itself (lower ADP =
market's preseason consensus best) rather than VBD -- there's no historical
FantasyPros projections archive to compute real retrospective VBD from, and
using that season's actual outcomes to rank draft-time picks would be
look-ahead bias. This is stored in a 'vbd' column (rank_value = -adp) purely
so the existing policy/roster machinery, which selects by max 'vbd', works
unchanged for both the live pool and the backtest pool.

K and DST get a zero real-outcomes placeholder (see historical_scorer.py) --
present in the pool so draft mechanics behave normally, excluded from scoring.
"""

import numpy as np
import pandas as pd

from config.league_settings import NUM_WEEKS
from src.backtest.historical_scorer import build_actual_weekly_points
from src.simulation.name_matching import FFC_POSITION_MAP, normalize_name


def build_backtest_pool(adp_players, season):
    """Returns a dataframe with: player, position, adp, stdev, vbd, actual_weekly."""
    adp_df = pd.DataFrame(adp_players).copy()
    adp_df["position"] = adp_df["position"].replace(FFC_POSITION_MAP)
    adp_df["vbd"] = -adp_df["adp"]  # ranking proxy only, see module docstring

    actual_points = build_actual_weekly_points(season)
    normalized_actual = {normalize_name(name): arr for name, arr in actual_points.items()}

    zero_weeks = np.zeros(NUM_WEEKS)
    skill_positions = {"QB", "RB", "WR", "TE"}
    missing = []

    def lookup(row):
        if row["position"] not in skill_positions:
            return zero_weeks
        key = normalize_name(row["name"])
        if key in normalized_actual:
            return normalized_actual[key]
        missing.append(row["name"])
        return zero_weeks

    adp_df["actual_weekly"] = adp_df.apply(lookup, axis=1)

    if missing:
        print(f"[backtest_pool] {season}: {len(missing)} skill players with no real outcomes match "
              f"(scored as 0, e.g. practice-squad-only or a name-matching gap): {missing}")

    return adp_df.rename(columns={"name": "player"})[
        ["player", "position", "adp", "stdev", "vbd", "actual_weekly"]
    ].reset_index(drop=True)
