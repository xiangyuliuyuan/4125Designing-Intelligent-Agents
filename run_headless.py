import math
import random
import sys
import time
import traceback
import argparse
from pathlib import Path

from app.context import create_simulation_data
from app.logging_config import configure_logging, get_logger, log_event, reset_logging
from robot import sensing
from simulation import runtime
from simulation.engine import advance_simulation_frame

logger = get_logger(__name__)

WORLD_SIZE = 1000
TOTAL_FRAMES = 3000
FRAME_DT = 1.0
DEFAULT_HEADLESS_LOG_NAME = "headless.log"
HEADLESS_LOG_PATH = Path("logs") / DEFAULT_HEADLESS_LOG_NAME


class FakeCanvas:
    def __init__(self, width=WORLD_SIZE, height=WORLD_SIZE):
        self.width = width
        self.height = height
        self._next_item_id = 1

    def _make_item_id(self):
        item_id = self._next_item_id
        self._next_item_id += 1
        return item_id

    def create_oval(self, *args, **kwargs):
        return self._make_item_id()

    def create_polygon(self, *args, **kwargs):
        return self._make_item_id()

    def create_line(self, *args, **kwargs):
        return self._make_item_id()

    def create_text(self, *args, **kwargs):
        return self._make_item_id()

    def create_rectangle(self, *args, **kwargs):
        return self._make_item_id()

    def delete(self, *args, **kwargs):
        return None

    def coords(self, *args, **kwargs):
        return ()

    def itemconfig(self, *args, **kwargs):
        return None

    def bind(self, *args, **kwargs):
        return None

    def after(self, *args, **kwargs):
        return None

    def after_cancel(self, *args, **kwargs):
        return None

    def winfo_width(self):
        return self.width

    def winfo_height(self):
        return self.height


class FakeStatLabel:
    def __init__(self):
        self.text = ""

    def config(self, *, text):
        self.text = text


def make_stats_vars():
    return {
        "debris": FakeStatLabel(),
        "active_bots": FakeStatLabel(),
        "avg_battery": FakeStatLabel(),
        "cats_count": FakeStatLabel(),
        "chargers_count": FakeStatLabel(),
        "runtime": FakeStatLabel(),
        "collected": FakeStatLabel(),
    }


def flush_logs():
    for handler in get_logger().handlers:
        try:
            handler.flush()
        except Exception:
            pass


def count_events(log_path):
    contents = Path(log_path).read_text(encoding="utf-8")
    return {
        "collision_detected": contents.count("event=collision_detected"),
        "cat.panic_jump": contents.count("event=cat.panic_jump"),
        "bot.physical_cat_freeze": contents.count("event=bot.physical_cat_freeze"),
    }


def reset_headless_log_files(log_path):
    for path in (Path(log_path), Path(log_path).with_suffix(".log.1")):
        if path.exists():
            path.unlink()


def _wrapped_distance(x1, y1, x2, y2):
    dx = x1 - x2
    dy = y1 - y2
    half = WORLD_SIZE / 2
    if dx > half: dx -= WORLD_SIZE
    elif dx < -half: dx += WORLD_SIZE
    if dy > half: dy -= WORLD_SIZE
    elif dy < -half: dy += WORLD_SIZE
    return math.sqrt(dx * dx + dy * dy)


def log_collisions(agents, cats):
    collisions = 0
    for bot in agents:
        for cat in cats:
            distance = _wrapped_distance(bot.x, bot.y, cat.x, cat.y)
            if distance < 30:
                collisions += 1
                log_event(
                    "WARNING",
                    logger,
                    event="collision_detected",
                    bot=bot.name,
                    cat=cat.name,
                    distance=distance,
                )
    return collisions


def log_cat_signals(agents, cats):
    for bot in agents:
        cat_l, cat_r = sensing.sense_cats(bot.sensorPositions, cats)
        log_event(
            "DEBUG",
            logger,
            event="headless.bot_cat_signal",
            bot=bot.name,
            catL=cat_l,
            catR=cat_r,
            cat_sum=cat_l + cat_r,
        )


def initialise_world(canvas, seed):
    random.seed(seed)
    simulation_data = create_simulation_data(canvas)
    return (
        simulation_data["agents"],
        simulation_data["passiveObjects"],
        simulation_data["count"],
        simulation_data["cats"],
        simulation_data["debris_count"],
        simulation_data["chargers"],
        simulation_data["start_time"],
    )


def run_simulation(seed=42, dt=FRAME_DT, frames=TOTAL_FRAMES, log_filename=DEFAULT_HEADLESS_LOG_NAME, emit_stdout=True):
    runtime.reset()
    log_path = Path("logs") / log_filename
    reset_headless_log_files(log_path)
    log_path = configure_logging(
        log_filename=log_filename,
        file_level="DEBUG",
        console_level="WARNING",
        max_bytes=20_000_000,
        backup_count=1,
        reset=True,
    )

    canvas = FakeCanvas()
    stats_vars = make_stats_vars()
    agents, passive_objects, count, cats, debris_count, chargers, start_time = initialise_world(canvas, seed)

    try:
        for _ in range(frames):
            runtime.simulation_tick += 1
            log_cat_signals(agents, cats)
            passive_objects, _snapshot = advance_simulation_frame(
                canvas,
                agents,
                passive_objects,
                count,
                cats,
                debris_count,
                stats_vars,
                start_time,
                chargers,
                dt=dt,
                now=start_time + (runtime.simulation_tick * dt),
            )
            log_collisions(agents, cats)
    except Exception as exc:
        log_event(
            "ERROR",
            logger,
            event="sim.headless_exception",
            reason="headless_loop_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            traceback=traceback.format_exc().strip().replace("\n", "\\n"),
        )
        flush_logs()
        reset_logging()
        raise

    flush_logs()
    event_counts = count_events(log_path)

    if emit_stdout:
        print(f"total_frames={frames}")
        print(f"seed={seed}")
        print(f"dt={dt}")
        print(f"collision_detected={event_counts['collision_detected']}")
        print(f"cat.panic_jump={event_counts['cat.panic_jump']}")
        print(f"bot.physical_cat_freeze={event_counts['bot.physical_cat_freeze']}")

    reset_logging()
    return {
        "frames": frames,
        "seed": seed,
        "dt": dt,
        "log_path": str(log_path),
        "collision_detected": event_counts["collision_detected"],
        "cat.panic_jump": event_counts["cat.panic_jump"],
        "bot.physical_cat_freeze": event_counts["bot.physical_cat_freeze"],
        "exit_code": 1 if event_counts["collision_detected"] > 0 else 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the simulation headlessly for reproducible regression checks.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dt", type=float, default=FRAME_DT)
    parser.add_argument("--frames", type=int, default=TOTAL_FRAMES)
    parser.add_argument("--log-filename", default=DEFAULT_HEADLESS_LOG_NAME)
    args = parser.parse_args(argv)

    result = run_simulation(
        seed=args.seed,
        dt=args.dt,
        frames=args.frames,
        log_filename=args.log_filename,
        emit_stdout=True,
    )
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
