import time

from simulation.passive_index import count_debris as indexed_debris_count


def count_debris(passive_objects):
    return indexed_debris_count(passive_objects)


def build_snapshot(passive_objects, agents, cats, chargers, count, start_time, now=None):
    if now is None:
        now = time.time()

    active_bots = len(agents)
    total_battery = sum(agent.battery for agent in agents if hasattr(agent, "battery"))
    avg_battery = total_battery // active_bots if active_bots > 0 else 0
    elapsed_time = now - start_time

    return {
        "debris": str(count_debris(passive_objects)),
        "active_bots": str(active_bots),
        "avg_battery": str(avg_battery),
        "cats_count": str(len(cats)),
        "chargers_count": str(len(chargers)),
        "runtime": f"{elapsed_time:.1f}s",
        "collected": str(count.dirtCollected),
    }
