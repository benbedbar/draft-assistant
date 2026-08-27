"""Part 5: full-scale Monte Carlo run across all 4 policies. Saves results to
data/processed/monte_carlo_results.json for the Part 6 backtest comparison
and eventual Streamlit app to consume.
"""

import json
import time
from pathlib import Path

import numpy as np

from src.ingestion.adp_ffc import fetch_adp
from src.ingestion.fantasypros_projections import load_projections
from src.ingestion.nflverse_historical import fetch_weekly_skill_position_data
from src.simulation.player_pool import build_player_pool
from src.simulation.monte_carlo import run_policy_monte_carlo, summarize
from src.uncertainty.empirical_distributions import build_empirical_buckets

NUM_SIMULATIONS = 5000
POLICIES = ["BPA", "Robust RB", "Zero RB", "Hero RB"]

print("Loading data...")
adp = fetch_adp(scoring="half-ppr", teams=10)
proj = load_projections("data/raw/fantasypros")
pool = build_player_pool(adp, proj)
weekly = fetch_weekly_skill_position_data([2019, 2020, 2021, 2022, 2023, 2024])
buckets = build_empirical_buckets(weekly)

results = {}
rng = np.random.default_rng(2026)
t_start = time.time()
for policy in POLICIES:
    t0 = time.time()
    vs_avg, vs_single = run_policy_monte_carlo(pool, buckets, policy, NUM_SIMULATIONS, rng)
    results[policy] = (vs_avg, vs_single)
    elapsed = time.time() - t0
    total_elapsed = time.time() - t_start
    print(f"[{total_elapsed:6.1f}s total] {policy:12s} done in {elapsed:5.1f}s "
          f"| vs_league_avg mean={vs_avg.mean():.3f} | vs_single_opp mean={vs_single.mean():.3f}", flush=True)

summary = summarize(results)
output = {
    "num_simulations": NUM_SIMULATIONS,
    "summary": summary,
    "raw": {p: {"vs_league_avg": r[0].tolist(), "vs_single_opponent": r[1].tolist()} for p, r in results.items()},
}
Path("data/processed").mkdir(parents=True, exist_ok=True)
with open("data/processed/monte_carlo_results.json", "w") as f:
    json.dump(output, f)

print()
print(f"Total time: {time.time() - t_start:.1f}s")
print()
print(f"{'Policy':12s} {'vs_league_avg':>16s} {'vs_single_opp':>16s} {'std':>8s} {'p10':>8s} {'p90':>8s}")
for policy, s in summary.items():
    la, so = s["vs_league_avg"], s["vs_single_opponent"]
    print(f"{policy:12s} {la['mean']:16.3f} {so['mean']:16.3f} {so['std']:8.3f} {so['p10']:8.3f} {so['p90']:8.3f}")
