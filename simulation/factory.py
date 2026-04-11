import random
import time

from app.logging_config import get_logger, log_event
from simulation.astar import AStar
from simulation.counting import Counter
from entities.cat import Cat
from entities.charger import Charger
from entities import dirt
from entities.lamp import Lamp
from robot.bot import Bot
from robot.brain import Brain
from robot.brain_coverage import CoverageMapBrain
from robot.brain_potential_field import PotentialFieldBrain
from robot.brain_qlearning import QLearningBrain
from simulation.passive_index import count_debris, invalidate_passive_object_index
from simulation.state import SimulationState

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Placement helpers — prevent entities from spawning on top of each other
# ---------------------------------------------------------------------------

# Minimum distance between a new entity and any debris obstacle.  Mirrors the
# A* robot clearance so that anything placed outside debris is also reachable.
_DEBRIS_CLEARANCE = 35.0
# Minimum distance between two chargers (they each need docking room).
_CHARGER_CLEARANCE = 50.0
_BOT_CLEARANCE = 60.0
_CAT_CLEARANCE = 40.0
_BOT_CAT_CLEARANCE = 90.0


def _overlaps_obstacles(x, y, clearance, placed_objects):
    """Return True if (x, y) is too close to any debris or charger."""
    for obj in placed_objects:
        is_debris = (
            isinstance(obj, (dirt.plusDirt, dirt.Dirt))
            and getattr(obj, "type", None) == "debris"
        )
        is_charger = isinstance(obj, Charger)
        if not is_debris and not is_charger:
            continue
        ox, oy = obj.getLocation()
        obj_radius = getattr(obj, "size", 0) if is_debris else 0
        min_dist = clearance + obj_radius
        if is_charger:
            min_dist = max(min_dist, _CHARGER_CLEARANCE)
        dx = x - ox
        dy = y - oy
        if dx * dx + dy * dy < min_dist * min_dist:
            return True
    return False


def _distance_sq(x1, y1, x2, y2):
    dx = x1 - x2
    dy = y1 - y2
    return dx * dx + dy * dy


def _overlaps_active_entities(
    x,
    y,
    agents=(),
    cats=(),
    min_distance_to_agents=0.0,
    min_distance_to_cats=0.0,
):
    if min_distance_to_agents > 0:
        min_agent_sq = min_distance_to_agents * min_distance_to_agents
        for agent in agents:
            if _distance_sq(x, y, agent.x, agent.y) < min_agent_sq:
                return True

    if min_distance_to_cats > 0:
        min_cat_sq = min_distance_to_cats * min_distance_to_cats
        for cat in cats:
            if _distance_sq(x, y, cat.x, cat.y) < min_cat_sq:
                return True

    return False


def _find_clear_position(placed_objects, clearance, margin=100,
                         world_size=1000, max_attempts=80,
                         agents=(), cats=(),
                         min_distance_to_agents=0.0,
                         min_distance_to_cats=0.0):
    """Return a random (x, y) that does not overlap obstacles/chargers."""
    for _ in range(max_attempts):
        x = random.randint(margin, world_size - margin)
        y = random.randint(margin, world_size - margin)
        if (
            not _overlaps_obstacles(x, y, clearance, placed_objects)
            and not _overlaps_active_entities(
                x,
                y,
                agents=agents,
                cats=cats,
                min_distance_to_agents=min_distance_to_agents,
                min_distance_to_cats=min_distance_to_cats,
            )
        ):
            return x, y
    # Fallback — return last attempt (very crowded world).
    logger.warning("_find_clear_position: exhausted %d attempts, returning potentially overlapping position (%d, %d)", max_attempts, x, y)
    return x, y


def buttonClicked(x, y, agents):
    nearest = None
    best_dist_sq = float("inf")
    for agent in agents:
        if isinstance(agent, Bot):
            dx = agent.x - x
            dy = agent.y - y
            dist_sq = dx * dx + dy * dy
            if dist_sq < best_dist_sq:
                best_dist_sq = dist_sq
                nearest = agent
    if nearest is not None:
        nearest.x = x
        nearest.y = y


def _make_bot(name, astar, brain_type="subsumption"):
    bot = Bot(name)
    bot.setAStar(astar)
    if brain_type == "potential_field":
        brain = PotentialFieldBrain(bot)
    elif brain_type == "qlearning":
        brain = QLearningBrain(bot)
    elif brain_type == "coverage":
        brain = CoverageMapBrain(bot)
    else:
        brain = Brain(bot)
    bot.setBrain(brain)
    return bot


def create_world(
    canvas,
    noOfBots=1,
    noOfLights=2,
    noOfCharger=1,
    amountOfDirt=300,
    dirt_plus=False,
    noOfCats=1,
    count=None,
    debris_count_initial=0,
    brain_type="subsumption",
):
    if count is None:
        count = Counter()

    state = SimulationState(count=count, debris_count=debris_count_initial, start_time=time.time())

    width = canvas.winfo_width()
    height = canvas.winfo_height()
    if width <= 1:
        width = 1000
    if height <= 1:
        height = 1000
    state.astar = AStar(width, height, grid_size=20)

    # --- Place chargers first (they are obstacles for placement purposes) ---
    for i in range(noOfCharger):
        charger = Charger(f"Charger{i}")
        cx, cy = _find_clear_position(state.passive_objects, _CHARGER_CLEARANCE,
                                      world_size=width)
        charger.centreX, charger.centreY = cx, cy
        state.passive_objects.append(charger)
        state.chargers.append(charger)
        charger.draw(canvas)

    # --- Place dirt / debris (debris must not overlap chargers or other debris) ---
    for i in range(amountOfDirt):
        if dirt_plus:
            trash_type = random.choice(["dust", "crumb", "paper", "liquid", "hair", "debris"])
            if trash_type == "debris":
                x, y = _find_clear_position(state.passive_objects, _DEBRIS_CLEARANCE,
                                            margin=10, world_size=width)
                state.debris_count += 1
            else:
                x, y = _find_clear_position(state.passive_objects, _DEBRIS_CLEARANCE,
                                            margin=10, world_size=width)
            dirt_obj = dirt.plusDirt(f"Dirt{i}", x, y, trash_type)
            state.passive_objects.append(dirt_obj)
            dirt_obj.draw_with_size(canvas)
        else:
            x, y = _find_clear_position(state.passive_objects, _DEBRIS_CLEARANCE,
                                        margin=10, world_size=width)
            dirt_obj = dirt.Dirt(f"Dirt{i}", x, y)
            state.passive_objects.append(dirt_obj)
            dirt_obj.draw(canvas)

    # --- Place lamps (avoid debris) ---
    for i in range(noOfLights):
        lamp = Lamp(f"Lamp{i}")
        lx, ly = _find_clear_position(state.passive_objects, _DEBRIS_CLEARANCE,
                                      world_size=width)
        lamp.centreX, lamp.centreY = lx, ly
        state.passive_objects.append(lamp)
        lamp.draw(canvas)

    # --- Place cats (avoid debris & existing actors) ---
    for i in range(noOfCats):
        cat = Cat(f"Cat{i}")
        cx, cy = _find_clear_position(state.passive_objects, _DEBRIS_CLEARANCE,
                                      world_size=width,
                                      agents=state.agents,
                                      cats=state.cats,
                                      min_distance_to_agents=_BOT_CAT_CLEARANCE,
                                      min_distance_to_cats=_CAT_CLEARANCE)
        cat.x, cat.y = cx, cy
        state.cats.append(cat)
        cat.draw(canvas)

    # --- Place bots (avoid debris & existing actors) ---
    for i in range(noOfBots):
        bot = _make_bot(f"Bot{i}", state.astar, brain_type=brain_type)
        bx, by = _find_clear_position(state.passive_objects, _DEBRIS_CLEARANCE,
                                      world_size=width,
                                      agents=state.agents,
                                      cats=state.cats,
                                      min_distance_to_agents=_BOT_CLEARANCE,
                                      min_distance_to_cats=_BOT_CAT_CLEARANCE)
        bot.x, bot.y = bx, by
        state.agents.append(bot)
        bot.draw(canvas)

    return state


def createObjects(
    canvas,
    noOfBots=1,
    noOfLights=2,
    noOfCharger=1,
    amountOfDirt=300,
    dirt_plus=False,
    noOfCats=1,
    count=None,
    debris_count_initial=0,
    brain_type="subsumption",
):
    state = create_world(
        canvas,
        noOfBots=noOfBots,
        noOfLights=noOfLights,
        noOfCharger=noOfCharger,
        amountOfDirt=amountOfDirt,
        dirt_plus=dirt_plus,
        noOfCats=noOfCats,
        count=count,
        debris_count_initial=debris_count_initial,
        brain_type=brain_type,
    )
    canvas.bind("<Button-1>", lambda event: buttonClicked(event.x, event.y, state.agents))
    return (
        state.agents,
        state.passive_objects,
        state.count,
        state.cats,
        state.debris_count,
        state.chargers,
        state.astar,
    )


def add_bot(canvas, agents, passiveObjects, astar, chargers, brain_type="subsumption", cats=()):
    bot_num = len(agents)
    bot = _make_bot(f"Bot{bot_num}", astar, brain_type=brain_type)
    bx, by = _find_clear_position(
        passiveObjects,
        _DEBRIS_CLEARANCE,
        agents=agents,
        cats=cats,
        min_distance_to_agents=_BOT_CLEARANCE,
        min_distance_to_cats=_BOT_CAT_CLEARANCE,
    )
    bot.x, bot.y = bx, by
    agents.append(bot)
    bot.draw(canvas)
    log_event("INFO", logger, event="control.bot_added", bot=bot.name, count_after=len(agents))
    return agents


def remove_bot(canvas, agents, chargers):
    if len(agents) > 1:
        removed = agents.pop()
        for charger in chargers:
            if charger.charging_bot is removed:
                charger.stop_charging()
        canvas.delete(removed.name)
        log_event("INFO", logger, event="control.bot_removed", bot=removed.name, count_after=len(agents))
    else:
        log_event("WARNING", logger, event="control.bot_remove_blocked", reason="minimum_one_bot")
    return agents


def add_cat(canvas, cats, passiveObjects=(), agents=()):
    cat_num = len(cats)
    cat = Cat(f"Cat{cat_num}")
    cx, cy = _find_clear_position(
        passiveObjects,
        _DEBRIS_CLEARANCE,
        agents=agents,
        cats=cats,
        min_distance_to_agents=_BOT_CAT_CLEARANCE,
        min_distance_to_cats=_CAT_CLEARANCE,
    )
    cat.x, cat.y = cx, cy
    cats.append(cat)
    cat.draw(canvas)
    log_event("INFO", logger, event="control.cat_added", cat=cat.name, count_after=len(cats))
    return cats


def remove_cat(canvas, cats):
    if len(cats) > 0:
        removed = cats.pop()
        canvas.delete(removed.name)
        log_event("INFO", logger, event="control.cat_removed", cat=removed.name, count_after=len(cats))
    else:
        log_event("WARNING", logger, event="control.cat_remove_blocked", reason="no_cat_available")
    return cats


def add_charger(canvas, passiveObjects, chargers):
    charger_num = len(chargers)
    charger = Charger(f"Charger{charger_num}")
    cx, cy = _find_clear_position(passiveObjects, _CHARGER_CLEARANCE)
    charger.centreX, charger.centreY = cx, cy
    passiveObjects.append(charger)
    chargers.append(charger)
    invalidate_passive_object_index(passiveObjects)
    charger.draw(canvas)
    log_event("INFO", logger, event="control.charger_added", charger=charger.name, count_after=len(chargers))
    return passiveObjects, chargers


def remove_charger(canvas, passiveObjects, chargers, agents):
    if len(chargers) > 1:
        removed = chargers.pop()
        occupied_bot = removed.charging_bot
        removed.stop_charging()
        for idx, obj in enumerate(passiveObjects):
            if obj is removed:
                passiveObjects.pop(idx)
                invalidate_passive_object_index(passiveObjects)
                break
        for agent in agents:
            if isinstance(agent, Bot) and (agent.target_charger is removed or agent is occupied_bot):
                agent.reset_charging_state()
        canvas.delete(removed.name)
        log_event("INFO", logger, event="control.charger_removed", charger=removed.name, count_after=len(chargers))
    else:
        log_event("WARNING", logger, event="control.charger_remove_blocked", reason="minimum_one_charger")
    return passiveObjects, chargers


def add_random_dirt_with_count(canvas, passiveObjects, debris_label, stats_vars):
    # 使用 canvas 实际尺寸生成坐标，避免超出画布
    width = canvas.winfo_width()
    height = canvas.winfo_height()
    if width <= 1:
        width = 1000
    if height <= 1:
        height = 1000
    x, y = _find_clear_position(passiveObjects, _DEBRIS_CLEARANCE,
                                margin=10, world_size=width)
    # 只选择可清扫的垃圾类型（排除 debris 障碍物）
    trash_type = random.choice(["dust", "crumb", "paper", "liquid", "hair"])
    dirt_obj = dirt.plusDirt(
        "Dirt_" + str(random.randint(10000, 99999)),
        x,
        y,
        trash_type,
    )
    passiveObjects.append(dirt_obj)
    invalidate_passive_object_index(passiveObjects)
    dirt_obj.draw_with_size(canvas)

    current_debris = count_debris(passiveObjects)
    stats_vars["debris"].config(text=str(current_debris))
    log_event(
        "INFO",
        logger,
        event="control.dirt_added",
        trash_type=trash_type,
        x=x,
        y=y,
        debris_count=current_debris,
    )
    return passiveObjects


def remove_dirt(canvas, passiveObjects, stats_vars):
    for idx in range(len(passiveObjects) - 1, -1, -1):
        obj = passiveObjects[idx]
        # 只移除可清扫的垃圾，不移除 debris 障碍物
        if isinstance(obj, (dirt.plusDirt, dirt.Dirt)):
            if hasattr(obj, "type") and obj.type == "debris":
                continue
            removed = passiveObjects.pop(idx)
            invalidate_passive_object_index(passiveObjects)
            canvas.delete(removed.name)
            log_event("INFO", logger, event="control.dirt_removed", dirt=removed.name)
            break

    current_debris = count_debris(passiveObjects)
    stats_vars["debris"].config(text=str(current_debris))
    return passiveObjects
