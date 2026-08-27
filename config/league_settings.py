"""League configuration — Boss League, forked from the original 2026-08-26.
Only difference from the original: 1 FLEX instead of 2 (everything else identical)."""

NUM_TEAMS = 10
MY_PICK_SLOT = 3  # 1-indexed, snake draft -- update if his pick slot differs
ROSTER_SIZE = 15

SCORING = "half_ppr"
RECEPTION_POINTS = 0.5

# Starting lineup slots. FLEX is eligible for RB/WR/TE.
STARTING_LINEUP = {
    "QB": 1,
    "RB": 2,
    "WR": 2,
    "TE": 1,
    "FLEX": 1,
    "K": 1,
    "DST": 1,
}
FLEX_ELIGIBLE = ("RB", "WR", "TE")

NUM_WEEKS = 17
