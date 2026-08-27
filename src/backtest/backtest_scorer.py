"""Score a backtest-drafted roster using real historical weekly outcomes --
no bucket sampling, since these are actual games that were actually played.
K/DST are excluded (see backtest_pool.py); everything else mirrors
season_scorer.py's two win-rate metrics for direct comparability with Part 5.
"""

import numpy as np

from config.league_settings import NUM_WEEKS
from src.simulation.lineup import optimal_lineup_score

SCORED_POSITIONS = {"QB", "RB", "WR", "TE"}


def simulate_actual_season_scores(roster, num_weeks=NUM_WEEKS):
    weekly_totals = np.empty(num_weeks)
    for week in range(num_weeks):
        week_points = [
            {"position": p["position"], "week_points": p["actual_weekly"][week]}
            for p in roster.players if p["position"] in SCORED_POSITIONS
        ]
        weekly_totals[week] = optimal_lineup_score(week_points)
    return weekly_totals


def score_backtest_draft(my_roster, opponent_rosters, rng, num_weeks=NUM_WEEKS):
    """Return (vs_league_avg, vs_single_opponent) weekly win rates. See season_scorer.py
    for what these two metrics mean."""
    my_weekly = simulate_actual_season_scores(my_roster, num_weeks)
    opp_weekly = np.array([simulate_actual_season_scores(r, num_weeks) for r in opponent_rosters.values()])
    opp_avg = opp_weekly.mean(axis=0)
    vs_league_avg = (my_weekly > opp_avg).mean()

    opponent_indices = rng.integers(0, opp_weekly.shape[0], size=num_weeks)
    single_opponent_scores = opp_weekly[opponent_indices, np.arange(num_weeks)]
    vs_single_opponent = (my_weekly > single_opponent_scores).mean()

    return vs_league_avg, vs_single_opponent
