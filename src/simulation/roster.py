"""Roster construction constraints shared by every draft policy.

These aren't part of any one policy's identity (BPA vs. Zero RB, etc.) --
they're baseline sanity rules a real drafter follows regardless of strategy:
don't roster a 3rd K, don't draft your kicker in round 4, and don't finish
the draft still missing a starting DST because a policy kept chasing RB
value instead. Every policy filters the available pool through these before
applying its own positional preference.
"""

from config.league_settings import ROSTER_SIZE

# Generous enough not to constrain any legitimate strategy (e.g. Zero RB
# rostering many WRs), just enough to block absurd allocations (5 kickers).
# QB is capped tighter than RB/WR/TE: it has no FLEX eligibility, so a 3rd QB
# has essentially zero realistic marginal value (you can only ever start one,
# and a 2nd already covers bye weeks) -- unlike bench RB/WR/TE depth, which
# still matters for FLEX, injuries, and trades.
POSITION_CAPS = {"QB": 2, "RB": 8, "WR": 8, "TE": 3, "K": 1, "DST": 1}

K_DST_MIN_ROUND = 12  # streaming K/DST is standard practice; no value in early picks
FORCE_K_ROUND = ROSTER_SIZE - 1   # round 14 of 15: guarantee a K gets drafted
FORCE_DST_ROUND = ROSTER_SIZE     # round 15 of 15: guarantee a DST gets drafted


class Roster:
    def __init__(self):
        self.players = []

    def add(self, player_row):
        self.players.append(player_row)

    def count(self, position):
        return sum(1 for p in self.players if p["position"] == position)

    def has(self, position):
        return self.count(position) > 0

    def is_full(self):
        return len(self.players) >= ROSTER_SIZE


def eligible_pool(available_df, roster, round_num):
    """Filter available players down to what roster-construction rules allow this round."""
    df = available_df

    for position, cap in POSITION_CAPS.items():
        if roster.count(position) >= cap:
            df = df[df["position"] != position]

    if round_num == FORCE_DST_ROUND and not roster.has("DST"):
        return df[df["position"] == "DST"]
    if round_num == FORCE_K_ROUND and not roster.has("K"):
        return df[df["position"] == "K"]

    if round_num < K_DST_MIN_ROUND:
        df = df[~df["position"].isin(["K", "DST"])]

    return df
