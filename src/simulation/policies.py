"""The 4 draft policies (Part 2). Each returns the player row to draft, given
the pool of players roster-construction rules currently allow (see roster.py)
and the round number. VBD is always the tiebreaker within whichever
positional rule a policy applies -- policies control *which players are in
play*, VBD decides *which one of those* to take.

Each policy's positional rule is expressed once via policy_intent() -- both
make_pick() (the simulator) and describe_intent() (the live app's guidance
text) read from it, so the two can never drift out of sync.
"""

from src.simulation.roster import eligible_pool

ROBUST_RB_ROUNDS = 3
ZERO_RB_ROUNDS = 4
HERO_RB_TAKE_ROUNDS = 2
HERO_RB_PIVOT_ROUNDS = 6


def _best(df):
    return df.loc[df["vbd"].idxmax()]


def policy_intent(policy_name, roster, round_num):
    """Return ("target"|"exclude"|"open", position_or_None) for this policy/round/roster."""
    if policy_name == "Robust RB" and round_num <= ROBUST_RB_ROUNDS:
        return "target", "RB"
    if policy_name == "Zero RB" and round_num <= ZERO_RB_ROUNDS:
        return "exclude", "RB"
    if policy_name == "Hero RB":
        if round_num <= HERO_RB_TAKE_ROUNDS and roster.count("RB") == 0:
            return "target", "RB"
        if round_num <= HERO_RB_PIVOT_ROUNDS and roster.count("RB") >= 1:
            return "exclude", "RB"
    return "open", None


def apply_intent(df, mode, position):
    if mode == "target":
        candidates = df[df["position"] == position]
        return candidates if len(candidates) else df
    if mode == "exclude":
        candidates = df[df["position"] != position]
        return candidates if len(candidates) else df
    return df


def describe_intent(mode, position):
    if mode == "target":
        return f"Target {position} -- take the best one available."
    if mode == "exclude":
        return f"Avoid {position} -- take the best player at any other position."
    return "Best player available -- any position."


def make_pick(policy_name, available_df, roster, round_num):
    """Apply roster constraints, then the named policy, and return the drafted player row."""
    df = eligible_pool(available_df, roster, round_num)
    if len(df) == 0:
        df = available_df  # constraints exhausted the pool (shouldn't happen in practice) -- fall back to anything available
    mode, position = policy_intent(policy_name, roster, round_num)
    return _best(apply_intent(df, mode, position))


POLICIES = ["BPA", "Robust RB", "Zero RB", "Hero RB"]
