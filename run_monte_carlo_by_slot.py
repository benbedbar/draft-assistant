"""Draft-slot sweep: run the Part 5 Monte Carlo for every snake-draft position
(1..NUM_TEAMS) x every policy, so a strategy can be chosen before the real
draft order is known.

Prints a slot x policy win-rate matrix and the best policy at each slot. If one
policy wins nearly everywhere, slot doesn't matter -- draft that. If the winner
shifts by slot, use the printed table as a lookup once the order is announced.

Saves data/processed/monte_carlo_by_slot.json for later reference.
"""

import json
import time
from pathlib import Path

import numpy as np

from config.league_settings import NUM_TEAMS
from src.ingestion.adp_ffc import fetch_adp
from src.ingestion.fantasypros_projections import load_projections
from src.ingestion.nflverse_historical import fetch_weekly_skill_position_data
from src.simulation.player_pool import build_player_pool
from src.simulation.monte_carlo import run_policy_monte_carlo
from src.uncertainty.empirical_distributions import build_empirical_buckets

# Lower than the single-slot script's 5000: this runs NUM_TEAMS x more cells.
# At ~0.1s/sim: 1000 -> ~70 min, 2000 -> ~2.3 hrs, 500 -> ~35 min.
# 1000 is enough to see whether one policy dominates all slots (the common
# case); re-run only the close slots at a higher count if margins are thin.
NUM_SIMULATIONS = 1000
POLICIES = ["BPA", "Robust RB", "Zero RB", "Hero RB"]
METRIC = "vs_single_opponent"  # the realistic H2H-style metric; see season_scorer.py

print("Loading data...")
adp = fetch_adp(scoring="half-ppr", teams=NUM_TEAMS)
proj = load_projections("data/raw/fantasypros")
pool = build_player_pool(adp, proj)
weekly = fetch_weekly_skill_position_data([2019, 2020, 2021, 2022, 2023, 2024])
buckets = build_empirical_buckets(weekly)

rng = np.random.default_rng(2026)
slots = list(range(1, NUM_TEAMS + 1))
results = {}  # slot -> {policy -> {"vs_league_avg": mean, "vs_single_opponent": mean}}

t_start = time.time()
for slot in slots:
    results[slot] = {}
    for policy in POLICIES:
        t0 = time.time()
        vs_avg, vs_single = run_policy_monte_carlo(
            pool, buckets, policy, NUM_SIMULATIONS, rng, my_slot=slot
        )
        results[slot][policy] = {
            "vs_league_avg": float(vs_avg.mean()),
            "vs_single_opponent": float(vs_single.mean()),
        }
        print(
            f"[{time.time() - t_start:6.1f}s] slot {slot:2d} | {policy:10s} "
            f"vs_single_opp={vs_single.mean():.3f} (cell {time.time() - t0:.1f}s)",
            flush=True,
        )

Path("data/processed").mkdir(parents=True, exist_ok=True)
with open("data/processed/monte_carlo_by_slot.json", "w") as f:
    json.dump({"num_simulations": NUM_SIMULATIONS, "metric": METRIC, "results":
              {str(s): v for s, v in results.items()}}, f)

# --- matrix ---
print()
header = f"{'slot':>4s} " + " ".join(f"{p:>11s}" for p in POLICIES) + f"   {'best':>11s}"
print(header)
print("-" * len(header))
best_by_slot = {}
for slot in slots:
    row = results[slot]
    best = max(POLICIES, key=lambda p: row[p][METRIC])
    best_by_slot[slot] = best
    cells = " ".join(f"{row[p][METRIC]:>11.3f}" for p in POLICIES)
    print(f"{slot:>4d} {cells}   {best:>11s}")

print()
winners = set(best_by_slot.values())
if len(winners) == 1:
    print(f"Same policy wins at every slot: {winners.pop()} -- draft order does not matter.")
else:
    print("Best policy varies by slot -- use the table above as a lookup once the order is set:")
    for slot in slots:
        print(f"  pick {slot:2d} -> {best_by_slot[slot]}")
print(f"\nTotal time: {time.time() - t_start:.1f}s")
