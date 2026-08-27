"""Optimal weekly starting lineup selection.

Same FLEX-allocation pattern as the VBD replacement-level calculation
(src/vbd/engine.py), just scoped to one 15-man roster and one week's
simulated scores instead of the whole league's season projections: fill
dedicated slots per position first, then let the league's FLEX slots go to
whichever remaining RB/WR/TE scored highest that week.
"""

from config.league_settings import FLEX_ELIGIBLE, STARTING_LINEUP


def optimal_lineup_score(week_points, starting_lineup=STARTING_LINEUP, flex_eligible=FLEX_ELIGIBLE):
    """week_points: list of {"position": ..., "week_points": ...} for one roster, one week."""
    by_position = {}
    for p in week_points:
        by_position.setdefault(p["position"], []).append(p["week_points"])
    for scores in by_position.values():
        scores.sort(reverse=True)

    total = 0.0
    flex_pool = []
    for position, slots in starting_lineup.items():
        if position == "FLEX":
            continue
        scores = by_position.get(position, [])
        total += sum(scores[:slots])
        if position in flex_eligible:
            flex_pool.extend(scores[slots:])

    flex_pool.sort(reverse=True)
    total += sum(flex_pool[: starting_lineup.get("FLEX", 0)])
    return total
