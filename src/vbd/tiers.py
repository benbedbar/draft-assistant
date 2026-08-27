"""Auto-tiering within each position: a new tier starts wherever the VBD gap
between consecutive players is unusually large relative to that position's
typical gap (mean + 1 std of consecutive gaps) -- a simple, standard way to
find real value cliffs instead of picking arbitrary fixed point breaks.
"""

import numpy as np


def assign_tiers(player_pool_df):
    df = player_pool_df.copy()
    df["tier"] = 0
    for _, group in df.groupby("position"):
        sorted_group = group.sort_values("vbd", ascending=False)
        vbd_vals = sorted_group["vbd"].to_numpy()
        idx = sorted_group.index

        if len(vbd_vals) <= 1:
            df.loc[idx, "tier"] = 1
            continue

        gaps = -np.diff(vbd_vals)
        threshold = gaps.mean() + gaps.std()

        tiers = [1]
        current_tier = 1
        for g in gaps:
            if threshold > 0 and g > threshold:
                current_tier += 1
            tiers.append(current_tier)
        df.loc[idx, "tier"] = tiers

    return df
