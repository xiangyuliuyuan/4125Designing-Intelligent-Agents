from entities import dirt
from app.logging_config import get_logger, log_event
from robot.state_view import derive_bot_mode

from simulation.passive_index import get_passive_object_index, invalidate_passive_object_index
from simulation import runtime

logger = get_logger(__name__)


def collect_dirt(bot, canvas, passive_objects, count, debris_count, current_time=None):
    to_delete = []
    if current_time is None:
        current_time = runtime.simulation_tick

    index = get_passive_object_index(passive_objects)
    for idx, obj in index.cleanable_dirt_entries:
        if isinstance(obj, (dirt.plusDirt, dirt.Dirt)) and bot.distanceTo(obj) < 30:
            if not obj.is_cleanable():
                continue

            trash_type = getattr(obj, "type", "dirt")
            if obj.clean(current_time):
                canvas.delete(obj.name)
                to_delete.append(idx)
                count.itemCollected(canvas, debris_count)
                log_event(
                    "INFO",
                    logger,
                    event="bot.clean_completed",
                    bot=bot.name,
                    mode=derive_bot_mode(bot),
                    reason="trash_cleared",
                    trash_type=trash_type,
                    score=count.dirtCollected,
                )
            elif isinstance(obj, dirt.plusDirt) and obj.clean_count > 0 and obj.clean_count != float("inf"):
                canvas.delete(obj.name)
                obj.draw_with_size(canvas)
                log_event(
                    "DEBUG",
                    logger,
                    event="bot.clean_progress",
                    bot=bot.name,
                    mode=derive_bot_mode(bot),
                    trash_type=trash_type,
                    remaining=obj.clean_count,
                )

    for idx in sorted(to_delete, reverse=True):
        del passive_objects[idx]
    if to_delete:
        invalidate_passive_object_index(passive_objects)
    return passive_objects
