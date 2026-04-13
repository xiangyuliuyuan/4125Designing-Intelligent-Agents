"""Shared utilities for experiment runners."""


def count_transitions(agents, frozen_agents, depleted_agents):
    """Count freeze/depletion state transitions (edges, not frames).

    Returns (cat_freezes, battery_depletions, next_frozen_agents, next_depleted_agents).
    """
    cat_freezes = 0
    battery_depletions = 0
    next_frozen_agents = set()
    next_depleted_agents = set()

    for agent in agents:
        agent_key = getattr(agent, "name", id(agent))

        if hasattr(agent, "brain") and (
            getattr(agent.brain, "is_cat_frozen", False)
            or getattr(agent.brain, "force_cat_freeze", False)
        ):
            next_frozen_agents.add(agent_key)
            if agent_key not in frozen_agents:
                cat_freezes += 1

        if getattr(agent, "battery", 1) <= 0:
            next_depleted_agents.add(agent_key)
            if agent_key not in depleted_agents:
                battery_depletions += 1

    return cat_freezes, battery_depletions, next_frozen_agents, next_depleted_agents
