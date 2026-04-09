import time
import traceback

from app.logging_config import get_logger, log_event
from simulation.counting import Counter
from simulation import runtime
from simulation.factory import createObjects
from simulation.passive_index import invalidate_passive_object_index
from simulation.stats import build_snapshot
from ui.theme import BTN_SUCCESS_BG, BTN_WARNING_BG

logger = get_logger(__name__)

WORLD_SIZE = 1000
PHYSICAL_CAT_FREEZE_DISTANCE = 90.0


def _wrapped_delta(target, current):
    delta = target - current
    half_world = WORLD_SIZE / 2
    if delta > half_world:
        delta -= WORLD_SIZE
    elif delta < -half_world:
        delta += WORLD_SIZE
    return delta


def _wrapped_distance_between_bot_and_cat(bot, cat):
    dx = _wrapped_delta(cat.x, bot.x)
    dy = _wrapped_delta(cat.y, bot.y)
    return (dx * dx + dy * dy) ** 0.5


def _close_cats_within_physical_freeze(bot, cats):
    close_cats = []
    for cat in cats:
        distance = _wrapped_distance_between_bot_and_cat(bot, cat)
        if distance < PHYSICAL_CAT_FREEZE_DISTANCE:
            close_cats.append((cat, distance))
    return close_cats


def _arm_physical_cat_freeze(bot, close_cats):
    if not close_cats or not hasattr(bot, "brain"):
        return False

    bot.brain.force_cat_freeze = True
    bot.brain.is_cat_frozen = True
    for cat, distance in close_cats:
        log_event(
            "INFO",
            logger,
            event="bot.physical_cat_freeze",
            bot=bot.name,
            cat=cat.name,
            distance=distance,
        )
    return True


def advance_simulation_frame(
    canvas,
    agents,
    passiveObjects,
    count,
    cats,
    debris_count,
    stats_vars,
    start_time,
    chargers,
    dt=1.0,
    now=None,
):
    for agent in agents:
        close_cats = _close_cats_within_physical_freeze(agent, cats)
        freeze_armed = _arm_physical_cat_freeze(agent, close_cats)
        try:
            agent.thinkAndAct(agents, passiveObjects, cats)
            agent.update(canvas, passiveObjects, dt)
        finally:
            if freeze_armed and hasattr(agent, "brain"):
                agent.brain.force_cat_freeze = False
                agent.brain.is_cat_frozen = False
        passiveObjects = agent.collectDirt(
            canvas,
            passiveObjects,
            count,
            debris_count,
            current_time=runtime.simulation_tick,
        )

    for cat in cats:
        cat.update(canvas, agents, dt, passiveObjects)

    for charger in chargers:
        canvas.delete(charger.name)
        charger.draw(canvas)

    snapshot = build_snapshot(passiveObjects, agents, cats, chargers, count, start_time, now=now or time.time())
    if stats_vars is not None:
        for key, value in snapshot.items():
            stats_vars[key].config(text=value)

    return passiveObjects, snapshot


def moveIt(
    canvas,
    agents,
    passiveObjects,
    count,
    cats,
    debris_count,
    stats_vars,
    start_time,
    speed_var,
    pause_button,
    chargers,
    astar,
):
    if runtime.reset_flag:
        runtime.reset_flag = False
        return

    if not runtime.simulation_running:
        runtime.after_id = canvas.after(
            50,
            moveIt,
            canvas,
            agents,
            passiveObjects,
            count,
            cats,
            debris_count,
            stats_vars,
            start_time,
            speed_var,
            pause_button,
            chargers,
            astar,
        )
        return

    runtime.simulation_speed = speed_var.get()
    runtime.simulation_tick += 1
    step_dt = 1.0

    try:
        passiveObjects, _snapshot = advance_simulation_frame(
            canvas,
            agents,
            passiveObjects,
            count,
            cats,
            debris_count,
            stats_vars,
            start_time,
            chargers,
            dt=step_dt,
            now=time.time(),
        )

    except Exception as exc:
        log_event(
            "ERROR",
            logger,
            event="sim.exception",
            reason="move_loop_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            traceback=traceback.format_exc().strip().replace("\n", "\\n"),
        )
        # Continue scheduling so the simulation doesn't freeze silently.
        # The next frame may recover (e.g. transient state issue).

    runtime.after_id = canvas.after(
        int(50 / runtime.simulation_speed),
        moveIt,
        canvas,
        agents,
        passiveObjects,
        count,
        cats,
        debris_count,
        stats_vars,
        start_time,
        speed_var,
        pause_button,
        chargers,
        astar,
    )


def reset_simulation(canvas, main_frame, stats_vars, speed_var, pause_button, brain_type="subsumption"):
    runtime.reset_flag = True
    runtime.simulation_running = False
    invalidate_passive_object_index()

    if runtime.after_id is not None:
        canvas.after_cancel(runtime.after_id)
        runtime.after_id = None

    canvas.delete("all")

    count = Counter()
    agents, passiveObjects, count, cats, debris_count, chargers, astar = createObjects(
        canvas,
        noOfBots=3,
        noOfLights=2,
        noOfCharger=2,
        dirt_plus=True,
        noOfCats=4,
        count=count,
        debris_count_initial=0,
        brain_type=brain_type,
    )

    stats_vars["collected"].config(text="0")
    stats_vars["debris"].config(text=str(debris_count))
    stats_vars["active_bots"].config(text=str(len(agents)))
    stats_vars["avg_battery"].config(text="1000")
    stats_vars["runtime"].config(text="0.0s")
    stats_vars["cats_count"].config(text=str(len(cats)))
    stats_vars["chargers_count"].config(text=str(len(chargers)))

    start_time = time.time()
    runtime.reset_flag = False
    runtime.simulation_running = True
    runtime.simulation_tick = 0
    pause_button.config(text="⏸ 暂停", bg=BTN_WARNING_BG)

    return agents, passiveObjects, count, cats, debris_count, chargers, astar, start_time


def toggle_pause(pause_button):
    runtime.simulation_running = not runtime.simulation_running
    if runtime.simulation_running:
        pause_button.config(text="⏸ 暂停", bg=BTN_WARNING_BG)
    else:
        pause_button.config(text="▶ 继续", bg=BTN_SUCCESS_BG)
