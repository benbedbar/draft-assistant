"""FantasyPros projections ingestion.

FantasyPros has no free self-serve API for individuals (their API product is
a paid enterprise offering) and their free-tier v2 API caps every response at
10 players/position regardless of endpoint. Instead this reads CSV exports
from their public site (full player pool, no cap):

  https://www.fantasypros.com/nfl/projections/<pos>.php
  (set the scoring toggle to "Half PPR" and the week selector to the
  season-long "Draft" view, then export one CSV per position)

Expected input: a directory containing one CSV per position, e.g.
  data/raw/fantasypros/qb.csv, rb.csv, wr.csv, te.csv, k.csv, dst.csv

Column names vary slightly by position page, but all include "Player" and a
final "FPTS" column. FPTS on the "Draft" view is a SEASON-LONG total, so it is
used directly as proj_points -- no per-game scaling.

The per-position usage columns (QB pass attempts, RB rush+receiving touches,
WR/TE receptions) are season totals as well, so they are divided by
GAMES_PLAYED_ESTIMATE to recover the per-game rate that Part 1 bucket
assignment expects (see src/uncertainty/buckets.py). The divisor is 16, not a
full 17: FantasyPros already shades injury-prone players' season totals down
for expected missed games, so their implied per-game role is (season total /
games actually played). Dividing by 16 reproduces the per-game rates from
FantasyPros' own weekly view (e.g. 117 projected catches / 16 ~= 7.3/g, which
keeps a WR1-volume receiver in the wr1 bucket rather than wr2). It is a single
uniform factor, so it does not disturb relative ranking within a position.
"""

from pathlib import Path

import pandas as pd

POSITIONS = ("qb", "rb", "wr", "te", "k", "dst")
GAMES_PLAYED_ESTIMATE = 16


def _clean_player_column(df):
    # FantasyPros bundles "Player Team" in one cell for some position pages,
    # e.g. "Christian McCaffrey SF". Team is a trailing all-caps token.
    if "Team" in df.columns:
        return df
    split = df["Player"].str.rsplit(" ", n=1, expand=True)
    df["Player"] = split[0]
    df["Team"] = split[1]
    return df


def _usage_columns(df, pos):
    """Per-game rate stats needed for Part 1 bucket assignment (see src/uncertainty/buckets.py).

    Source columns are season totals on the "Draft" projection pages, so each
    is divided by GAMES_PLAYED_ESTIMATE to land on the per-game scale the
    bucket thresholds use.

    Pandas auto-suffixes repeated CSV headers (e.g. QB's two "ATT" columns --
    pass then rush) as COL, COL.1, ... in file order, so the bare name always
    refers to the first occurrence. That's pass attempts for QB and rush
    attempts for RB/WR -- exactly the columns we want by name alone.
    """
    touches = receptions = attempts = None
    if pos == "qb":
        attempts = pd.to_numeric(df["ATT"], errors="coerce") / GAMES_PLAYED_ESTIMATE
    elif pos == "rb":
        season_touches = (
            pd.to_numeric(df["ATT"], errors="coerce")
            + pd.to_numeric(df["REC"], errors="coerce")
        )
        touches = season_touches / GAMES_PLAYED_ESTIMATE
    elif pos in ("wr", "te"):
        receptions = pd.to_numeric(df["REC"], errors="coerce") / GAMES_PLAYED_ESTIMATE
    return touches, receptions, attempts


def load_projections(raw_dir):
    """Load and combine per-position FantasyPros CSV exports into one table.

    Returns columns: player, position, team, proj_points, touches, receptions, attempts
    (proj_points is a season-long total; the last three are per-game rates, NaN
    where not applicable to that position -- used to assign each player to a
    Part 1 usage bucket).
    """
    raw_dir = Path(raw_dir)
    frames = []
    missing = []
    for pos in POSITIONS:
        path = raw_dir / f"{pos}.csv"
        if not path.exists():
            missing.append(path.name)
            continue
        df = pd.read_csv(path)
        df = _clean_player_column(df)
        touches, receptions, attempts = _usage_columns(df, pos)
        frames.append(pd.DataFrame({
            "player": df["Player"].str.strip(),
            "position": pos.upper(),
            "team": df["Team"].fillna("").astype(str).str.strip(),
            "proj_points": pd.to_numeric(df["FPTS"], errors="coerce"),
            "touches": touches,
            "receptions": receptions,
            "attempts": attempts,
        }))

    if missing:
        raise FileNotFoundError(
            f"Missing FantasyPros CSV exports in {raw_dir}: {missing}. "
            "Export half-PPR season-long ('Draft') projections per position from "
            "fantasypros.com/nfl/projections/<pos>.php and save them there."
        )

    return pd.concat(frames, ignore_index=True).dropna(subset=["proj_points"])
