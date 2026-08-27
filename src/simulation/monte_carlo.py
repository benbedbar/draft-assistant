"""Part 5: Monte Carlo simulation engine. Runs many full drafts per policy,
scores each with the weekly-variance season simulation, and aggregates.

Tracks both win-rate metrics from season_scorer.score_draft: vs. the league
average (the brief's literal Part 5.3 spec, structurally inflated by
averaging away opponent variance) and vs. a single randomly-assigned weekly
opponent (closer to a real H2H matchup outcome). See season_scorer.py.
"""

import numpy as np

from config.league_settings import MY_PICK_SLOT
from src.simulation.draft_simulator import simulate_draft
from src.simulation.season_scorer import score_draft


def run_policy_monte_carlo(player_pool_df, buckets, policy_name, num_simulations, rng=None,
                            my_slot=MY_PICK_SLOT):
    """Return arrays (vs_league_avg, vs_single_opponent), each length num_simulations.

    my_slot is the 1-indexed snake-draft position drafted from; defaults to the
    league config. Sweep it across 1..NUM_TEAMS when the real draft slot is not
    yet known (see run_monte_carlo_by_slot.py).
    """
    rng = rng or np.random.default_rng()
    vs_league_avg = np.empty(num_simulations)
    vs_single_opponent = np.empty(num_simulations)
    for i in range(num_simulations):
        my_roster, opponent_rosters = simulate_draft(player_pool_df, policy_name, my_slot=my_slot, rng=rng)
        vs_league_avg[i], vs_single_opponent[i], _, _ = score_draft(my_roster, opponent_rosters, buckets, rng)
    return vs_league_avg, vs_single_opponent


def run_all_policies(player_pool_df, buckets, policies, num_simulations, rng=None,
                      my_slot=MY_PICK_SLOT):
    """Return {policy_name: (vs_league_avg_array, vs_single_opponent_array)}."""
    rng = rng or np.random.default_rng()
    return {
        policy_name: run_policy_monte_carlo(player_pool_df, buckets, policy_name, num_simulations, rng,
                                            my_slot=my_slot)
        for policy_name in policies
    }


def _stats(arr):
    return {
        "mean": arr.mean(),
        "std": arr.std(),
        "p10": np.percentile(arr, 10),
        "p90": np.percentile(arr, 90),
    }


def summarize(results):
    """results: {policy_name: (vs_league_avg, vs_single_opponent)} -> nested stats dict."""
    return {
        policy_name: {
            "vs_league_avg": _stats(vs_avg),
            "vs_single_opponent": _stats(vs_single),
        }
        for policy_name, (vs_avg, vs_single) in results.items()
    }
