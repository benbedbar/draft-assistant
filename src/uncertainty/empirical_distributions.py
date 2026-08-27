"""Empirical weekly-outcome distributions per usage bucket.

No theoretical distribution (normal, etc.) is assumed anywhere here -- each
bucket's "distribution" is built entirely from real historical weeks.

Buckets store RATIOS (that week's points / that player-season's own average
points), not raw point totals. A raw-points bucket would flatten every player
in it to the bucket's generic average -- e.g. Ja'Marr Chase and a replacement
WR2 both landing in a "moderate target volume" bucket would get scored
identically, discarding the entire VBD/projection signal that made Chase
worth drafting in the first place. Storing ratios instead preserves the
empirical variance *shape* (skew, boom/bust tails, real week-to-week noise)
while letting the caller anchor the *location* to each specific player's own
projected weekly mean: simulated_week = ratio * (player_proj_points / 17).
"""

import numpy as np

from src.uncertainty.buckets import assign_buckets

MIN_BUCKET_SIZE = 50  # below this, the empirical distribution is too noisy to trust
MIN_SEASON_WEEKS = 4  # player-seasons with fewer weeks give an unstable personal mean
MIN_SEASON_MEAN = 1.0  # excludes effectively-inactive player-seasons (undefined ratio)


def _add_ratio_column(weekly_df):
    season_stats = (
        weekly_df.groupby(["player_id", "season"])["half_ppr_points"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "season_mean", "count": "season_weeks"})
    )
    df = weekly_df.merge(season_stats, on=["player_id", "season"])
    df = df[(df["season_weeks"] >= MIN_SEASON_WEEKS) & (df["season_mean"] >= MIN_SEASON_MEAN)]
    df = df.copy()
    df["ratio"] = df["half_ppr_points"] / df["season_mean"]
    return df


def build_empirical_buckets(weekly_df):
    """Return {bucket_name: np.ndarray of point ratios} from weekly player data."""
    ratio_df = _add_ratio_column(weekly_df)
    bucketed = assign_buckets(ratio_df)
    buckets = {}
    for bucket_name, group in bucketed.groupby("bucket"):
        buckets[bucket_name] = group["ratio"].to_numpy()
    return buckets


def bucket_sizes(buckets):
    return {name: len(arr) for name, arr in buckets.items()}


def warn_small_buckets(buckets, min_size=MIN_BUCKET_SIZE):
    return {name: n for name, n in bucket_sizes(buckets).items() if n < min_size}


def bootstrap_sample_ratio(buckets, bucket_name, size=1, rng=None):
    """Draw `size` realistic performance ratios (relative to a player's own mean) for a bucket."""
    rng = rng or np.random.default_rng()
    arr = buckets[bucket_name]
    return rng.choice(arr, size=size, replace=True)


def sample_weekly_points(buckets, bucket_name, player_weekly_mean, size=1, rng=None):
    """Simulate realistic weekly point totals for a specific player.

    player_weekly_mean should be that player's own projected points/week
    (e.g. season proj_points / 17) -- the bucket only supplies the shape of
    week-to-week variance around it.
    """
    ratios = bootstrap_sample_ratio(buckets, bucket_name, size=size, rng=rng)
    return ratios * player_weekly_mean
