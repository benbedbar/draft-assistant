"""Unified draft-time player pool: merges FFC ADP with FantasyPros projections/VBD.

Two sources, two naming conventions to reconcile:
  - Skill players: matched by normalized name (case, punctuation, suffixes,
    and unicode accents stripped -- e.g. FFC's "Eddy Pineiro" vs FantasyPros'
    "Eddy Piñeiro").
  - Team defenses: FFC labels these "{City} Defense" (e.g. "Seattle Defense")
    while FantasyPros uses the full team name ("Seattle Seahawks") with no
    team-abbreviation column at all. Name-matching can't bridge that, so DST
    rows are matched on team abbreviation instead, via a static full-team-name
    -> abbreviation table.

Any ADP player left unmatched after both passes is dropped with a warning
(logged, not silently discarded) -- usually a genuine gap in the projections
source (e.g. a just-drafted rookie FantasyPros hasn't projected yet) rather
than a matching failure.
"""

import pandas as pd

from src.simulation.name_matching import FFC_POSITION_MAP, TEAM_NAME_TO_ABBR, normalize_name
from src.uncertainty.buckets import assign_buckets
from src.vbd.engine import compute_replacement_levels, compute_vbd


def build_player_pool(adp_players, projections_df):
    """Merge ADP with projections+VBD+bucket assignment into one draft-ready table.

    Returns a dataframe with: player, position, team, adp, stdev, proj_points,
    vbd, bucket, plus usage columns (touches/receptions/attempts) for skill positions.
    """
    adp_df = pd.DataFrame(adp_players).copy()
    adp_df["position"] = adp_df["position"].replace(FFC_POSITION_MAP)

    repl = compute_replacement_levels(projections_df)
    proj_vbd = compute_vbd(projections_df, repl)
    skill_mask = proj_vbd["position"].isin(["QB", "RB", "WR", "TE"])
    proj_vbd["bucket"] = None
    proj_vbd.loc[skill_mask, "bucket"] = assign_buckets(proj_vbd.loc[skill_mask, :])["bucket"]

    adp_df["match_key"] = adp_df["name"].apply(normalize_name)
    proj_vbd["match_key"] = proj_vbd["player"].apply(normalize_name)
    proj_no_name = proj_vbd.drop(columns="player")  # ADP's "name" is the surviving player identity

    is_dst = adp_df["position"] == "DST"

    name_matched = adp_df[~is_dst].merge(proj_no_name, on="match_key", how="left", suffixes=("", "_proj"))

    dst_left = adp_df[is_dst].copy()
    dst_left["team_abbr"] = dst_left["team"]
    proj_dst = proj_no_name[proj_no_name["position"] == "DST"].copy()
    proj_dst["team_abbr"] = proj_vbd.loc[proj_dst.index, "player"].map(TEAM_NAME_TO_ABBR)
    dst_matched = dst_left.merge(proj_dst, on="team_abbr", how="left", suffixes=("", "_proj"))

    merged = pd.concat([name_matched, dst_matched], ignore_index=True)

    unmatched = merged[merged["proj_points"].isna()]
    if len(unmatched):
        names = unmatched["name"].tolist()
        print(f"[player_pool] Dropping {len(unmatched)} ADP players with no projections match: {names}")

    matched = merged.dropna(subset=["proj_points"]).copy()
    matched = matched.rename(columns={"name": "player"})
    keep = ["player", "position", "adp", "stdev", "proj_points", "vbd", "bucket",
            "touches", "receptions", "attempts"]
    return matched[keep].reset_index(drop=True)
