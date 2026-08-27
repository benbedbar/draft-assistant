"""Usage-based archetype bucket assignment.

Bucketing happens per player-week, on that week's actual usage -- not a
season-long label -- so a player who was a bellcow in October and a committee
back in December contributes weeks to both buckets. This is what lets us pool
across many players' weeks into one robust empirical distribution instead of
trusting any single player's short in-season sample (see Part 1 of the brief).

Thresholds are simple, round-number usage cutoffs matching the archetype
language in the brief ("RB1 with 15+ touches/game", etc.) rather than
statistically-fit breakpoints -- the goal is pooling weeks with clearly
similar roles, not a precision classifier.

WR/TE bucket on receptions rather than targets: draft-time projections (Part
5/6 use this same bucketing to score projected players, not just historical
weeks) only expose a projected receptions rate, not targets, so both the
historical fit and the projection-time assignment need to use the metric
that's available in both places. Thresholds are set accordingly (receptions
run below targets at a ~65-70% league-average catch rate).
"""

import pandas as pd


def _rb_bucket(touches):
    if touches >= 15:
        return "bellcow"
    if touches >= 8:
        return "committee"
    return "low_volume"


def _wr_bucket(receptions):
    if receptions >= 7:
        return "wr1"
    if receptions >= 4:
        return "wr2"
    return "low_volume_flex"


def _te_bucket(receptions):
    if receptions >= 5:
        return "high_volume"
    return "streaming_low_volume"


def _qb_bucket(attempts):
    if attempts >= 25:
        return "starter"
    return "backup_or_spot_start"


_BUCKET_FUNCS = {
    "RB": ("touches", _rb_bucket),
    "WR": ("receptions", _wr_bucket),
    "TE": ("receptions", _te_bucket),
    "QB": ("attempts", _qb_bucket),
}


def assign_buckets(df):
    """Add a 'bucket' column (e.g. 'RB_bellcow') to a dataframe with per-position usage columns.

    Works on either weekly historical rows or per-player projected rate rows,
    as long as the position-appropriate usage column (touches/receptions/attempts) is present.
    """
    df = df.copy()
    bucket_labels = pd.Series(index=df.index, dtype=object)
    for position, (usage_col, bucket_fn) in _BUCKET_FUNCS.items():
        mask = df["position"] == position
        bucket_labels.loc[mask] = df.loc[mask, usage_col].fillna(0).apply(bucket_fn)
    df["bucket"] = df["position"] + "_" + bucket_labels
    return df
