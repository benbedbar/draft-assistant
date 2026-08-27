"""Part 6: full backtest across 5 valid historical seasons x 4 policies.
2022 excluded -- FFC's historical ADP archive for that year only has 124
entries, short of the 150 needed for a full 10-team/15-round draft.
Saves results for the Part 5-vs-Part-6 comparison table.
"""

import json
import time

import numpy as np

from src.backtest.backtest_runner import run_backtest, summarize_backtest

SEASONS = [2019, 2020, 2021, 2023, 2024]
POLICIES = ["BPA", "Robust RB", "Zero RB", "Hero RB"]
NUM_SIMULATIONS = 500

rng = np.random.default_rng(2026)
t0 = time.time()
results = run_backtest(SEASONS, POLICIES, NUM_SIMULATIONS, rng)
print(f"Total time: {time.time() - t0:.1f}s", flush=True)

summary = summarize_backtest(results)

output = {
    "seasons": SEASONS,
    "num_simulations": NUM_SIMULATIONS,
    "summary": {
        policy: {
            "mean_vs_league_avg": s["mean_vs_league_avg"],
            "mean_vs_single_opponent": s["mean_vs_single_opponent"],
            "per_season_vs_league_avg": {str(k): v for k, v in s["per_season_vs_league_avg"].items()},
            "per_season_vs_single_opponent": {str(k): v for k, v in s["per_season_vs_single_opponent"].items()},
        }
        for policy, s in summary.items()
    },
}
with open("data/processed/backtest_results.json", "w") as f:
    json.dump(output, f)

print()
print(f"{'Policy':12s} {'vs_league_avg':>16s} {'vs_single_opp':>16s}")
for policy, s in summary.items():
    print(f"{policy:12s} {s['mean_vs_league_avg']:16.3f} {s['mean_vs_single_opponent']:16.3f}")
