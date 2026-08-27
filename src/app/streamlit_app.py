"""Part 7: live draft assistant.

Everything expensive (ADP/projections fetch, VBD, tiers) runs once at startup
behind st.cache_data -- every click during the draft is a lookup against an
already-computed table, not a re-run of any simulation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from config.league_settings import FLEX_ELIGIBLE, MY_PICK_SLOT as DEFAULT_PICK_SLOT, NUM_TEAMS, ROSTER_SIZE, STARTING_LINEUP
from src.ingestion.adp_ffc import fetch_adp
from src.ingestion.fantasypros_projections import load_projections
from src.simulation.draft_simulator import snake_order
from src.simulation.player_pool import build_player_pool
from src.simulation.policies import POLICIES, apply_intent, describe_intent, policy_intent
from src.simulation.roster import Roster, eligible_pool
from src.vbd.tiers import assign_tiers

st.set_page_config(page_title="Draft Assistant", layout="wide")

TEAM_SLOTS = list(range(1, NUM_TEAMS + 1))
PICK_ORDER = snake_order(NUM_TEAMS, ROSTER_SIZE)

# Optional friendly labels for known managers, keyed by pick slot; any slot not
# listed just shows "Team N". Left generic so the app can be shared across leagues.
TEAM_NAMES = {}


def team_label(slot):
    if slot == st.session_state.my_pick_slot:
        return "Me"
    return TEAM_NAMES.get(slot, f"Team {slot}")


@st.cache_data
def load_pool():
    adp = fetch_adp(scoring="half-ppr", teams=NUM_TEAMS)
    proj = load_projections("data/raw/fantasypros")
    pool = build_player_pool(adp, proj)
    pool = assign_tiers(pool)
    return pool.sort_values("vbd", ascending=False).reset_index(drop=True)


POOL = load_pool()

if "drafted" not in st.session_state:
    st.session_state.drafted = {}       # player name -> team_slot (int), insertion-ordered
    st.session_state.pick_history = []  # ordered list of player names, for undo
if "my_pick_slot" not in st.session_state:
    st.session_state.my_pick_slot = DEFAULT_PICK_SLOT


def draft_player(name, team_slot):
    st.session_state.drafted[name] = team_slot
    st.session_state.pick_history.append(name)


def undo_last():
    if not st.session_state.pick_history:
        return
    name = st.session_state.pick_history.pop()
    del st.session_state.drafted[name]


def reset_draft():
    st.session_state.drafted = {}
    st.session_state.pick_history = []


def team_players(slot):
    """This team's drafted player rows, in the order they were picked."""
    names = [n for n, s in st.session_state.drafted.items() if s == slot]
    rows = POOL.set_index("player").loc[names].reset_index() if names else POOL.iloc[0:0]
    return rows.to_dict("records")


# ---------- Sidebar ----------
with st.sidebar:
    st.title("Draft Assistant")
    st.number_input(
        "My pick slot", min_value=1, max_value=NUM_TEAMS, key="my_pick_slot",
        help="Update this as soon as the draft order is set — everything below re-labels automatically.",
    )
    policy_name = st.selectbox("Strategy", POLICIES, index=POLICIES.index("Zero RB"))
    st.caption("Zero RB had the highest simulated win rate at every draft slot (10-team half-PPR, 1-FLEX). Hero RB was a close second.")
    st.divider()
    st.metric("Overall picks made", len(st.session_state.drafted))
    st.metric("My picks made", len(team_players(st.session_state.my_pick_slot)))
    st.divider()
    if st.button("Undo last pick", use_container_width=True):
        undo_last()
        st.rerun()
    if st.button("Reset draft", type="secondary", use_container_width=True):
        reset_draft()
        st.rerun()

remaining = POOL[~POOL["player"].isin(st.session_state.drafted.keys())]
my_players = team_players(st.session_state.my_pick_slot)
my_roster = Roster()
for p in my_players:
    my_roster.add(p)
my_round = len(my_players) + 1

next_pick_num = len(st.session_state.drafted)
on_the_clock = PICK_ORDER[next_pick_num] if next_pick_num < len(PICK_ORDER) else None

st.title(f"Pick Slot {st.session_state.my_pick_slot} &middot; Round {my_round}".replace("&middot;", "·"))

# ---------- Draft entry, my roster, league rosters ----------
col_form, col_roster, col_league = st.columns([1, 1.2, 1.8])

with col_form:
    st.subheader("Mark a player drafted")
    if on_the_clock is not None:
        st.caption(f"On the clock: overall pick {next_pick_num + 1} — **{team_label(on_the_clock)}**")
    with st.form("draft_form", clear_on_submit=True):
        player_name = st.selectbox("Player", remaining["player"].tolist(), index=None, placeholder="Search a player...")
        default_idx = TEAM_SLOTS.index(on_the_clock) if on_the_clock is not None else 0
        team_slot = st.selectbox("Drafted by", TEAM_SLOTS, index=default_idx, format_func=team_label)
        submitted = st.form_submit_button("Mark drafted", type="primary")
        if submitted and player_name:
            draft_player(player_name, team_slot)
            st.rerun()

with col_roster:
    st.subheader("My roster")
    if my_players:
        st.dataframe(
            [{"Pos": p["position"], "Player": p["player"], "VBD": round(p["vbd"], 1)} for p in my_players],
            hide_index=True, use_container_width=True,
        )
    else:
        st.caption("No picks yet.")

    fill_lines = []
    for pos, slots in STARTING_LINEUP.items():
        if pos == "FLEX":
            continue
        have = my_roster.count(pos)
        fill_lines.append(f"{pos}: {have}/{slots}")
    st.caption(" &nbsp; ".join(fill_lines).replace("&nbsp;", " "))

with col_league:
    st.subheader("League rosters")
    tabs = st.tabs([team_label(slot) for slot in TEAM_SLOTS])
    for slot, tab in zip(TEAM_SLOTS, tabs):
        with tab:
            players = team_players(slot)
            if players:
                st.dataframe(
                    [{"Pos": p["position"], "Player": p["player"], "VBD": round(p["vbd"], 1)} for p in players],
                    hide_index=True, use_container_width=True,
                )
            else:
                st.caption("No picks yet.")

st.divider()

# ---------- Recommendation ----------
st.subheader("Recommended for your turn")

mode, target_pos = policy_intent(policy_name, my_roster, my_round)
guidance = describe_intent(mode, target_pos)
st.info(f"**{policy_name}** — {guidance}")

eligible = eligible_pool(remaining, my_roster, my_round)
targeted = apply_intent(eligible, mode, target_pos)
shortlist = targeted.sort_values("vbd", ascending=False).head(10)

st.dataframe(
    shortlist[["player", "position", "adp", "proj_points", "vbd", "tier"]]
    .rename(columns={"player": "Player", "position": "Pos", "adp": "ADP", "proj_points": "Proj Pts", "vbd": "VBD", "tier": "Tier"})
    .style.format({"ADP": "{:.1f}", "Proj Pts": "{:.1f}", "VBD": "{:+.1f}"}),
    hide_index=True, use_container_width=True,
)

# ---------- Tier-break alerts ----------
alerts = []
for pos in ["QB", "RB", "WR", "TE"]:
    pos_remaining = remaining[remaining["position"] == pos].sort_values("tier")
    if pos_remaining.empty:
        continue
    top_tier = pos_remaining["tier"].iloc[0]
    count_in_tier = (pos_remaining["tier"] == top_tier).sum()
    if count_in_tier <= 2:
        alerts.append(f"**{pos}** — only {count_in_tier} player(s) left in the current top tier (Tier {top_tier}).")

if alerts:
    st.warning("Tier break imminent:\n\n" + "\n\n".join(alerts))

st.divider()

# ---------- Opponent summary ----------
st.subheader("Opponent summary")
summary_rows = []
for slot in TEAM_SLOTS:
    if slot == st.session_state.my_pick_slot:
        continue
    players = team_players(slot)
    counts = {pos: 0 for pos in ["QB", "RB", "WR", "TE", "K", "DST"]}
    for p in players:
        counts[p["position"]] += 1
    last_pick = players[-1]["player"] if players else "—"
    summary_rows.append({"Team": team_label(slot), "Picks": len(players), **counts, "Most Recent": last_pick})

st.dataframe(summary_rows, hide_index=True, use_container_width=True)

st.divider()

# ---------- Full remaining board ----------
st.subheader("Remaining players")
pos_filter = st.multiselect("Filter by position", ["QB", "RB", "WR", "TE", "K", "DST"], default=[])
board = remaining if not pos_filter else remaining[remaining["position"].isin(pos_filter)]
st.dataframe(
    board[["player", "position", "adp", "proj_points", "vbd", "tier"]]
    .rename(columns={"player": "Player", "position": "Pos", "adp": "ADP", "proj_points": "Proj Pts", "vbd": "VBD", "tier": "Tier"})
    .style.format({"ADP": "{:.1f}", "Proj Pts": "{:.1f}", "VBD": "{:+.1f}"}),
    hide_index=True, use_container_width=True, height=420,
)
