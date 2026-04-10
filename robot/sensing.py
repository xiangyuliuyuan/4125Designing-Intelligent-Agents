import math

from entities.cat import Cat
from robot.motion import wrapped_delta as _wrapped_delta
from simulation.passive_index import get_passive_object_index


def _is_bot(agent):
    """Check if agent is a Bot without importing to avoid circular imports."""
    return hasattr(agent, 'x') and hasattr(agent, 'y') and hasattr(agent, 'brain')


def calculate_sensor_values(sensor_positions, obj_x, obj_y, intensity, max_distance=float("inf")):
    dxL = _wrapped_delta(obj_x, sensor_positions[0])
    dyL = _wrapped_delta(obj_y, sensor_positions[1])
    dxR = _wrapped_delta(obj_x, sensor_positions[2])
    dyR = _wrapped_delta(obj_y, sensor_positions[3])
    distL = math.sqrt(dxL * dxL + dyL * dyL)
    distR = math.sqrt(dxR * dxR + dyR * dyR)
    valL = intensity / (distL * distL) if 0 < distL < max_distance else 0.0
    valR = intensity / (distR * distR) if 0 < distR < max_distance else 0.0
    return valL, valR


def sense_debris(sensor_positions, passive_objects):
    debrisL = 0.0
    debrisR = 0.0
    index = get_passive_object_index(passive_objects)
    for obj in index.debris_objects:
        lx, ly = obj.getLocation()
        dL, dR = calculate_sensor_values(sensor_positions, lx, ly, 1000000, 150)
        debrisL += dL
        debrisR += dR
    return debrisL, debrisR


def sense_light(sensor_positions, passive_objects):
    lightL = 0.0
    lightR = 0.0
    index = get_passive_object_index(passive_objects)
    for obj in index.lamp_objects:
        lx, ly = obj.getLocation()
        dL, dR = calculate_sensor_values(sensor_positions, lx, ly, 200000)
        lightL += dL
        lightR += dR
    return lightL, lightR


def sense_other_bots(sensor_positions, agents, current_bot):
    lightL = 0.0
    lightR = 0.0
    for agent in agents:
        if agent is not current_bot and _is_bot(agent):
            dL, dR = calculate_sensor_values(sensor_positions, agent.x, agent.y, 8000000, 200)
            lightL += dL
            lightR += dR
    return lightL, lightR


def sense_cats(sensor_positions, cats):
    catL = 0.0
    catR = 0.0
    for cat in cats:
        if isinstance(cat, Cat):
            cx, cy = cat.getLocation()
            dL, dR = calculate_sensor_values(sensor_positions, cx, cy, 6000000, 220)
            catL += dL
            catR += dR
    return catL, catR


def sense_chargers(sensor_positions, passive_objects):
    chargerL = 0.0
    chargerR = 0.0
    index = get_passive_object_index(passive_objects)
    for obj in index.charger_objects:
        lx, ly = obj.getLocation()
        dL, dR = calculate_sensor_values(sensor_positions, lx, ly, 200000)
        chargerL += dL
        chargerR += dR
    return chargerL, chargerR
