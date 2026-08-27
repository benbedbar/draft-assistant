"""Value-over-replacement (VBD) engine.

Replacement level per position = the projected points of the best player who
would NOT be a starter anywhere in the league (i.e. rank = total_starters + 1
at that position) -- the "who's on waivers" baseline, not the last starter.

FLEX-eligible positions (RB/WR/TE) need a simultaneous allocation: dedicated
slots are filled per-position first, then the league's FLEX slots go to
whichever remaining RB/WR/TE players have the highest points regardless of
position. That flex allocation is exactly how two FLEX spots (vs. one)
disproportionately raise replacement level for whichever position is deepest
at the margin -- there's no need to hardcode which position that is, the
ranking does it.
"""

from config.league_settings import FLEX_ELIGIBLE, NUM_TEAMS, STARTING_LINEUP


def _replacement_rank_points(ranked_points, num_starters):
    """Points of the best non-starter at a position (rank = num_starters + 1)."""
    idx = num_starters  # 0-indexed, so this IS the (num_starters + 1)-th player
    if idx >= len(ranked_points):
        return ranked_points[-1] if len(ranked_points) else 0.0
    return ranked_points[idx]


def compute_replacement_levels(projections_df, num_teams=NUM_TEAMS,
                                starting_lineup=STARTING_LINEUP, flex_eligible=FLEX_ELIGIBLE):
    """Return {position: replacement_level_points}."""
    ranked = {
        pos: projections_df.loc[projections_df["position"] == pos, "proj_points"]
        .sort_values(ascending=False).to_numpy()
        for pos in projections_df["position"].unique()
    }

    replacement = {}

    # Non-flex positions: straightforward rank cutoff.
    for pos, slots in starting_lineup.items():
        if pos == "FLEX" or pos not in ranked:
            continue
        if pos in flex_eligible:
            continue  # handled below with flex allocation
        replacement[pos] = _replacement_rank_points(ranked[pos], num_teams * slots)

    # Flex-eligible positions: allocate dedicated slots, then flex slots by raw points.
    dedicated_starters = {}
    flex_pool = []
    for pos in flex_eligible:
        if pos not in ranked:
            continue
        n_dedicated = num_teams * starting_lineup.get(pos, 0)
        dedicated_starters[pos] = n_dedicated
        leftover = ranked[pos][n_dedicated:]
        flex_pool.extend((points, pos) for points in leftover)

    flex_pool.sort(key=lambda x: x[0], reverse=True)
    n_flex_slots = num_teams * starting_lineup.get("FLEX", 0)
    flex_starters_taken = flex_pool[:n_flex_slots]

    flex_count_by_pos = {pos: 0 for pos in flex_eligible}
    for _, pos in flex_starters_taken:
        flex_count_by_pos[pos] += 1

    for pos in flex_eligible:
        if pos not in ranked:
            continue
        total_starters = dedicated_starters[pos] + flex_count_by_pos[pos]
        replacement[pos] = _replacement_rank_points(ranked[pos], total_starters)

    return replacement


def compute_vbd(projections_df, replacement_levels=None):
    """Return projections_df with a 'vbd' column: proj_points - replacement level."""
    if replacement_levels is None:
        replacement_levels = compute_replacement_levels(projections_df)
    df = projections_df.copy()
    df["vbd"] = df.apply(
        lambda row: row["proj_points"] - replacement_levels[row["position"]],
        axis=1,
    )
    return df.sort_values("vbd", ascending=False).reset_index(drop=True)
