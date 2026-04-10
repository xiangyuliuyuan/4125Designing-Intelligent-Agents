from simulation.passive_index import invalidate_passive_object_index


simulation_running = True
simulation_speed = 1.0
reset_flag = False
after_id = None
simulation_tick = 0
generation = 0


def reset():
    global simulation_running, simulation_speed, reset_flag, after_id, simulation_tick, generation
    simulation_running = True
    simulation_speed = 1.0
    reset_flag = False
    after_id = None
    simulation_tick = 0
    generation = 0
    invalidate_passive_object_index()
