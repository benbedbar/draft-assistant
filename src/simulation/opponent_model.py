"""ADP-weighted random opponent drafting model (Part 4).

Rather than inventing an arbitrary "how tightly opponents follow ADP" knob,
this uses each player's own empirically observed ADP standard deviation
(from the Fantasy Football Calculator data -- real historical variance in
where that exact player got drafted) as the spread of a normal distribution
centered on their mean ADP. A player rarely drafted off their ADP (e.g. a
locked-in 1.01) gets a tight distribution; a volatile ADP player gets a wide
one -- reaches and falls emerge naturally per-player instead of from a single
global temperature parameter.
"""

import numpy as np
from scipy.stats import norm

MIN_STDEV = 1.0  # floor so near-zero-variance players don't collapse to a point mass


def compute_weights(pool_df, current_pick):
    """Weight of each available player being taken at this pick, given their ADP."""
    stdev = pool_df["stdev"].clip(lower=MIN_STDEV)
    return norm.pdf(current_pick, loc=pool_df["adp"], scale=stdev)


def sample_pick(pool_df, current_pick, rng):
    """Sample one player from the pool, weighted by ADP-implied likelihood of going now."""
    weights = compute_weights(pool_df, current_pick)
    if weights.sum() == 0:
        weights = np.ones(len(pool_df))
    probs = weights / weights.sum()
    idx = rng.choice(pool_df.index, p=probs)
    return pool_df.loc[idx]


def simulate_opponent_pick(pool_df, current_pick, rng):
    """Sample a pick and return (picked_player_row, remaining_pool_df)."""
    picked = sample_pick(pool_df, current_pick, rng)
    remaining = pool_df.drop(index=picked.name)
    return picked, remaining
