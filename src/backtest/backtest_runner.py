"""Part 6: backtest each policy against real historical seasons.

Per season: build that season's real ADP + real-outcomes pool, simulate many
drafts (opponents are randomized via the ADP-weighted model, so a single draft
would be noisy), score each with real weekly outcomes, and average.
"""

import numpy as np

from src.backtest.backtest_pool import build_backtest_pool
from src.backtest.backtest_scorer import score_backtest_draft
from src.ingestion.adp_ffc import fetch_adp
from src.simulation.draft_simulator import simulate_draft


def run_backtest_season(pool, policy_name, num_simulations, rng=None):
    """Return (vs_league_avg_array, vs_single_opponent_array) for one season/policy."""
    rng = rng or np.random.default_rng()
    vs_league_avg = np.empty(num_simulations)
    vs_single_opponent = np.empty(num_simulations)
    for i in range(num_simulations):
        my_roster, opponent_rosters = simulate_draft(pool, policy_name, rng=rng)
        vs_league_avg[i], vs_single_opponent[i] = score_backtest_draft(my_roster, opponent_rosters, rng)
    return vs_league_avg, vs_single_opponent


def run_backtest(seasons, policies, num_simulations, rng=None):
    """Return {policy_name: {season: (vs_league_avg_array, vs_single_opponent_array)}}.

    Builds each season's pool once and reuses it across all policies, since
    the pool (ADP + real outcomes) doesn't depend on the policy being tested.
    """
    rng = rng or np.random.default_rng()
    results = {policy_name: {} for policy_name in policies}
    for season in seasons:
        adp_players = fetch_adp(scoring="half-ppr", teams=10, year=season)
        pool = build_backtest_pool(adp_players, season)
        min_needed = 10 * 15  # NUM_TEAMS * ROSTER_SIZE
        if len(pool) < min_needed:
            raise ValueError(
                f"{season}'s historical ADP pool only has {len(pool)} players, "
                f"need >= {min_needed} for a full draft. Drop this season from the backtest."
            )
        for policy_name in policies:
            results[policy_name][season] = run_backtest_season(pool, policy_name, num_simulations, rng)
    return results


def summarize_backtest(results):
    """{policy: {season: (la, so)}} -> {policy: {mean_across_seasons, per_season: {season: mean}}}"""
    summary = {}
    for policy_name, by_season in results.items():
        per_season_la = {season: arr[0].mean() for season, arr in by_season.items()}
        per_season_so = {season: arr[1].mean() for season, arr in by_season.items()}
        summary[policy_name] = {
            "mean_vs_league_avg": np.mean(list(per_season_la.values())),
            "mean_vs_single_opponent": np.mean(list(per_season_so.values())),
            "per_season_vs_league_avg": per_season_la,
            "per_season_vs_single_opponent": per_season_so,
        }
    return summary
