import time

from simulation.counting import Counter
from simulation import runtime
from simulation.engine import moveIt
from simulation.factory import createObjects


DEFAULT_WORLD_CONFIG = {
    "noOfBots": 3,
    "noOfLights": 2,
    "noOfCharger": 2,
    "dirt_plus": True,
    "noOfCats": 4,
    "debris_count_initial": 0,
}


def create_simulation_data(canvas, config=None):
    world_config = dict(DEFAULT_WORLD_CONFIG)
    if config:
        world_config.update(config)

    count = Counter()
    agents, passive_objects, count, cats, debris_count, chargers, astar = createObjects(
        canvas,
        count=count,
        **world_config,
    )
    return {
        "agents": agents,
        "passiveObjects": passive_objects,
        "count": count,
        "cats": cats,
        "debris_count": debris_count,
        "chargers": chargers,
        "astar": astar,
        "start_time": time.time(),
    }


def apply_reset_result(simulation_data, result):
    (
        simulation_data["agents"],
        simulation_data["passiveObjects"],
        simulation_data["count"],
        simulation_data["cats"],
        simulation_data["debris_count"],
        simulation_data["chargers"],
        simulation_data["astar"],
        simulation_data["start_time"],
    ) = result
    return simulation_data


def schedule_simulation(canvas, simulation_data, stats_vars, speed_var, pause_button):
    runtime.after_id = canvas.after(
        50,
        moveIt,
        canvas,
        simulation_data["agents"],
        simulation_data["passiveObjects"],
        simulation_data["count"],
        simulation_data["cats"],
        simulation_data["debris_count"],
        stats_vars,
        simulation_data["start_time"],
        speed_var,
        pause_button,
        simulation_data["chargers"],
        simulation_data["astar"],
    )
    return runtime.after_id
