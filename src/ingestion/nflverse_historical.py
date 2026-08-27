"""Historical weekly fantasy data ingestion from nflverse (via nfl_data_py).

Covers QB/RB/WR/TE only — nflverse's weekly player data has no player-level
rows for kickers or team defenses. Those two positions are handled separately
(see Part 1 notes) since they carry far less VBD spread and don't need the
same empirical-bucket treatment as skill positions.
"""

import nfl_data_py as nfl

SKILL_POSITIONS = ("QB", "RB", "WR", "TE")


def fetch_weekly_skill_position_data(years):
    """Return REG-season weekly rows for QB/RB/WR/TE with half-PPR points computed.

    half_ppr = fantasy_points_ppr - 0.5 * receptions
    (nflverse ships standard and full-PPR fantasy_points; half-PPR isn't
    precomputed, but is a fixed linear adjustment away from full PPR.)
    """
    df = nfl.import_weekly_data(years, downcast=True)
    df = df[(df["season_type"] == "REG") & (df["position"].isin(SKILL_POSITIONS))].copy()
    df["half_ppr_points"] = df["fantasy_points_ppr"] - 0.5 * df["receptions"]
    # Touches use receptions (not targets) so this matches the usage metric
    # available from draft-time projections, which only expose receptions.
    df["touches"] = df["carries"].fillna(0) + df["receptions"].fillna(0)
    keep = [
        "player_id", "player_display_name", "position", "recent_team",
        "season", "week", "receptions", "targets", "carries", "attempts",
        "touches", "half_ppr_points",
    ]
    return df[keep].reset_index(drop=True)
