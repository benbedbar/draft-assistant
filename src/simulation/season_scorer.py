"""Weekly-variance season scoring (Part 5.3): sample each roster's players from
their empirical usage bucket for each of 17 weeks, set the optimal lineup each
week, and compare my score against the average of the 9 opponents' scores.

K and DST have no nflverse player-level history to build a real bucket from
(see src/ingestion/nflverse_historical.py), so their weekly variance borrows
the shape of an existing bucket with comparable real-world week-to-week
volatility: K ~ QB_starter (both a stable, once-a-week, single-scoring-event
role), DST ~ WR_wr2 (moderate boom/bust range). This is a named simplification,
not data-derived, because those two positions rarely differentiate the draft
*strategies* being compared here -- they're drafted in the same late rounds
under every policy.
"""

import numpy as np
import pandas as pd

from config.league_settings import NUM_WEEKS
from src.simulation.lineup import optimal_lineup_score
from src.uncertainty.empirical_distributions import sample_weekly_points

KDST_BUCKET_SUBSTITUTE = {"K": "QB_starter", "DST": "WR_wr2"}


def _bucket_for(player):
    bucket = player.get("bucket")
    if pd.notna(bucket):
        return bucket
    return KDST_BUCKET_SUBSTITUTE[player["position"]]


def simulate_season_weekly_scores(roster, buckets, rng, num_weeks=NUM_WEEKS):
    """Return an array of length num_weeks: this roster's optimal-lineup score each week."""
    weekly_totals = np.empty(num_weeks)
    for week in range(num_weeks):
        week_points = []
        for player in roster.players:
            bucket_name = _bucket_for(player)
            weekly_mean = player["proj_points"] / num_weeks
            pts = sample_weekly_points(buckets, bucket_name, weekly_mean, size=1, rng=rng)[0]
            week_points.append({"position": player["position"], "week_points": pts})
        weekly_totals[week] = optimal_lineup_score(week_points)
    return weekly_totals


def score_draft(my_roster, opponent_rosters, buckets, rng, num_weeks=NUM_WEEKS):
    """Return win rates against two baselines, plus the raw weekly scores:

    - vs_league_avg: my score vs. the mean of all 9 opponents' scores each
      week (Part 5.3's literal spec). Averaging 9 independent random scores
      cuts the baseline's variance ~9x, so this reads as a very high win rate
      for any team with even a modest true edge -- it answers "am I above
      average", not "would I have beaten this week's actual opponent".
    - vs_single_opponent: my score vs. one randomly-assigned opponent per
      week (roughly emulating a round-robin H2H schedule), with that
      opponent's full week-to-week variance intact -- closer to what a real
      matchup outcome looks like.
    """
    my_weekly = simulate_season_weekly_scores(my_roster, buckets, rng, num_weeks)
    opp_weekly = np.array([
        simulate_season_weekly_scores(r, buckets, rng, num_weeks)
        for r in opponent_rosters.values()
    ])
    opp_avg = opp_weekly.mean(axis=0)
    vs_league_avg = (my_weekly > opp_avg).mean()

    opponent_indices = rng.integers(0, opp_weekly.shape[0], size=num_weeks)
    single_opponent_scores = opp_weekly[opponent_indices, np.arange(num_weeks)]
    vs_single_opponent = (my_weekly > single_opponent_scores).mean()

    return vs_league_avg, vs_single_opponent, my_weekly, opp_avg
