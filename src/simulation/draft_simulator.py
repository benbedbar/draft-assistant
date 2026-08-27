"""Full single-draft simulation: snake order, ADP-weighted opponents, policy-driven me."""

from config.league_settings import MY_PICK_SLOT, NUM_TEAMS, ROSTER_SIZE
from src.simulation.opponent_model import sample_pick
from src.simulation.policies import make_pick
from src.simulation.roster import Roster, eligible_pool


def snake_order(num_teams, num_rounds):
    """List of team slots (1-indexed) in overall-pick order for a snake draft."""
    order = []
    for round_num in range(1, num_rounds + 1):
        round_order = range(1, num_teams + 1) if round_num % 2 == 1 else range(num_teams, 0, -1)
        order.extend(round_order)
    return order


def simulate_draft(player_pool_df, policy_name, my_slot=MY_PICK_SLOT,
                    num_teams=NUM_TEAMS, num_rounds=ROSTER_SIZE, rng=None):
    """Run one full mock draft. Returns (my_roster, {team_slot: opponent_roster})."""
    pool = player_pool_df.reset_index(drop=True).copy()
    order = snake_order(num_teams, num_rounds)

    my_roster = Roster()
    opponent_rosters = {slot: Roster() for slot in range(1, num_teams + 1) if slot != my_slot}

    for i, team_slot in enumerate(order):
        overall_pick = i + 1
        round_num = (i // num_teams) + 1

        if team_slot == my_slot:
            picked = make_pick(policy_name, pool, my_roster, round_num)
            my_roster.add(picked)
        else:
            opponent_roster = opponent_rosters[team_slot]
            candidates = eligible_pool(pool, opponent_roster, round_num)
            if len(candidates) == 0:
                candidates = pool
            picked = sample_pick(candidates, overall_pick, rng)
            opponent_roster.add(picked)

        pool = pool.drop(index=picked.name)

    return my_roster, opponent_rosters
