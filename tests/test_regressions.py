import types
import unittest
import runpy
import tkinter
import time
import warnings
import io
import math
import tempfile
from collections import deque
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_main_module():
    source = (PROJECT_ROOT / "main.py").read_text(encoding="utf-8")
    trimmed = source.rsplit("\nmain()", 1)[0] + "\n"
    module = types.ModuleType("sim_main")
    exec(compile(trimmed, str(PROJECT_ROOT / "main.py"), "exec"), module.__dict__)
    return module


class DummyCanvas:
    def __init__(self):
        self.after_calls = []
        self.operations = []

    def delete(self, *args, **kwargs):
        self.operations.append(("delete", args, kwargs))

    def create_polygon(self, *args, **kwargs):
        self.operations.append(("create_polygon", args, kwargs))

    def create_oval(self, *args, **kwargs):
        self.operations.append(("create_oval", args, kwargs))

    def create_text(self, *args, **kwargs):
        self.operations.append(("create_text", args, kwargs))

    def create_line(self, *args, **kwargs):
        self.operations.append(("create_line", args, kwargs))

    def create_rectangle(self, *args, **kwargs):
        self.operations.append(("create_rectangle", args, kwargs))

    def bind(self, *args, **kwargs):
        pass

    def after(self, delay, callback, *args):
        self.after_calls.append((delay, callback, args))
        return len(self.after_calls)


class FakeRoot:
    def __init__(self):
        self.calls = []

    def resizable(self, width_flag, height_flag):
        self.calls.append((width_flag, height_flag))

    def update_idletasks(self):
        pass


class FakeParent:
    def __init__(self, root):
        self.root = root

    def winfo_toplevel(self):
        return self.root


class DummyTkCanvas:
    def __init__(self, parent, width, height, bg, **kwargs):
        self.parent = parent
        self.width = width
        self.height = height
        self.bg = bg
        self.packed = False

    def pack(self, *args, **kwargs):
        self.packed = True


class FakeTkWidget:
    def __init__(self, parent=None, **kwargs):
        self.parent = parent
        self.kwargs = kwargs
        self.calls = []

    def pack(self, *args, **kwargs):
        self.calls.append(("pack", args, kwargs))

    def config(self, **kwargs):
        self.kwargs.update(kwargs)
        self.calls.append(("config", kwargs))

    def cget(self, key):
        return self.kwargs.get(key, "")

    def winfo_toplevel(self):
        if self.parent and hasattr(self.parent, "winfo_toplevel"):
            return self.parent.winfo_toplevel()
        return self.parent


class FakeTkCanvas(DummyCanvas):
    def __init__(self, parent=None, width=1000, height=1000, bg="white", **kwargs):
        super().__init__()
        self.parent = parent
        self.width = width
        self.height = height
        self.bg = bg
        self.kwargs = kwargs
        self.packed = False

    def pack(self, *args, **kwargs):
        self.packed = True

    def winfo_width(self):
        return self.width

    def winfo_height(self):
        return self.height

    def winfo_toplevel(self):
        if self.parent and hasattr(self.parent, "winfo_toplevel"):
            return self.parent.winfo_toplevel()
        return self.parent


class FakeTkVar:
    def __init__(self, value=None):
        self.value = value
        self.callbacks = []

    def get(self):
        return self.value

    def set(self, value):
        self.value = value
        for callback in self.callbacks:
            callback()

    def trace(self, *_args):
        callback = _args[-1]
        self.callbacks.append(callback)

    def trace_add(self, mode, callback):
        self.callbacks.append(callback)


class FakeTkRoot(FakeTkWidget):
    def __init__(self):
        super().__init__(None)
        self._geometry = "1000x1000+0+0"
        self.bindings = []
        self.title_value = None

    def title(self, value):
        self.title_value = value

    def bind(self, event, callback):
        self.bindings.append((event, callback))

    def update_idletasks(self):
        pass

    def geometry(self, value=None):
        if value is not None:
            self._geometry = value
        return self._geometry

    def resizable(self, width_flag, height_flag):
        self.calls.append(("resizable", width_flag, height_flag))

    def destroy(self):
        pass

    def mainloop(self):
        pass

    def winfo_toplevel(self):
        return self


class FakeTkModule:
    RAISED = "raised"
    X = "x"
    TOP = "top"
    LEFT = "left"
    HORIZONTAL = "horizontal"

    def __init__(self):
        self.created_roots = []

    def Tk(self):
        root = FakeTkRoot()
        self.created_roots.append(root)
        return root

    def Frame(self, parent=None, **kwargs):
        return FakeTkWidget(parent, **kwargs)

    def LabelFrame(self, parent=None, **kwargs):
        return FakeTkWidget(parent, **kwargs)

    def Label(self, parent=None, **kwargs):
        return FakeTkWidget(parent, **kwargs)

    def Scale(self, parent=None, **kwargs):
        return FakeTkWidget(parent, **kwargs)

    def Button(self, parent=None, **kwargs):
        return FakeTkWidget(parent, **kwargs)

    def Canvas(self, parent=None, width=1000, height=1000, bg="white", **kwargs):
        return FakeTkCanvas(parent, width=width, height=height, bg=bg, **kwargs)

    def DoubleVar(self, value=None):
        return FakeTkVar(value=value)

    def StringVar(self, value=None):
        return FakeTkVar(value=value)

    def OptionMenu(self, parent, variable, default, *values, **kwargs):
        widget = FakeTkWidget(parent, variable=variable, default=default, values=values, **kwargs)
        return widget


class RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_main_module()

    def make_bot(self, name="Bot0"):
        bot = self.mod.Bot(name)
        bot.setBrain(self.mod.Brain(bot))
        bot.setAStar(self.mod.AStar(1000, 1000, 20))
        return bot

    def test_initialise_uses_toplevel_window_for_resizable(self):
        fake_root = FakeRoot()
        fake_parent = FakeParent(fake_root)
        original_canvas = self.mod.tk.Canvas
        self.mod.tk.Canvas = DummyTkCanvas
        try:
            canvas = self.mod.initialise(fake_parent)
        finally:
            self.mod.tk.Canvas = original_canvas

        self.assertEqual(fake_root.calls, [(False, False)])
        self.assertIsInstance(canvas, DummyTkCanvas)
        self.assertTrue(canvas.packed)

    def test_initialise_does_not_lock_real_tk_window_to_one_pixel(self):
        from ui.window import create_main_window

        window, frame = create_main_window(tk_module=self.mod.tk)
        try:
            self.mod.initialise(frame)
            window.update_idletasks()
            size = window.geometry().split("+", 1)[0]
            width, height = map(int, size.split("x"))
        finally:
            window.destroy()

        self.assertGreater(width, 100)
        self.assertGreater(height, 100)

    def test_main_delegates_to_run_app(self):
        fake_tk = FakeTkModule()
        original_tk = self.mod.tk
        run_calls = {"count": 0}

        def fake_run_app():
            run_calls["count"] += 1

        self.mod.tk = fake_tk
        self.mod.run_app = fake_run_app
        try:
            self.mod.main()
        finally:
            self.mod.tk = original_tk

        self.assertEqual(run_calls["count"], 1)
        self.assertEqual(len(fake_tk.created_roots), 0)

    def test_entities_package_exports_domain_types(self):
        from entities.cat import Cat as EntityCat
        from entities.charger import Charger as EntityCharger
        from entities.dirt import Dirt as EntityDirt
        from entities.dirt import plusDirt as EntityPlusDirt

        self.assertIs(self.mod.Cat, EntityCat)
        self.assertIs(self.mod.Charger, EntityCharger)
        self.assertIs(self.mod.dirt.Dirt, EntityDirt)
        self.assertIs(self.mod.dirt.plusDirt, EntityPlusDirt)

    def test_renderer_draws_entity_shapes(self):
        from entities.charger import Charger as EntityCharger
        from entities.dirt import Dirt as EntityDirt
        from ui import renderer

        canvas = DummyCanvas()

        charger = EntityCharger("Charger0")
        charger.centreX = 100
        charger.centreY = 120
        renderer.draw_charger(canvas, charger)

        dirt_obj = EntityDirt("Dirt0", x=30, y=40)
        renderer.draw_dirt(canvas, dirt_obj)

        operations = [name for name, _args, _kwargs in canvas.operations]
        self.assertIn("create_rectangle", operations)
        self.assertIn("create_oval", operations)

    def test_app_context_creates_initial_simulation_data(self):
        from app.context import create_simulation_data

        canvas = FakeTkCanvas(width=1000, height=1000)
        simulation_data = create_simulation_data(canvas)

        self.assertEqual(len(simulation_data["agents"]), 3)
        self.assertEqual(len(simulation_data["cats"]), 4)
        self.assertEqual(len(simulation_data["chargers"]), 2)
        self.assertIn("start_time", simulation_data)

    def test_control_panel_builds_pause_button(self):
        from ui.control_panel import build_basic_controls

        fake_tk = FakeTkModule()
        parent = fake_tk.Frame()
        _frame, pause_button, reset_button = build_basic_controls(
            parent,
            pause_command=lambda: None,
            reset_command=lambda: None,
            tk_module=fake_tk,
        )

        self.assertEqual(pause_button.kwargs["text"], "⏸ 暂停")
        self.assertEqual(reset_button.kwargs["text"], "🔄 重置")

    def test_logging_routes_info_to_file_and_warning_to_console(self):
        import logging

        from app.logging_config import configure_logging, log_event, reset_logging, LOG_NAMESPACE
        from simulation import runtime

        self.addCleanup(reset_logging)

        console_stream = io.StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = configure_logging(
                log_dir=temp_dir,
                file_level="INFO",
                console_level="WARNING",
                console_stream=console_stream,
                reset=True,
            )
            runtime.simulation_tick = 7
            log_event("INFO", "test.logging", event="test.info_event", actor="tester")
            log_event("WARNING", "test.logging", event="test.warning_event", actor="tester")

            app_logger = logging.getLogger(LOG_NAMESPACE)
            for handler in app_logger.handlers:
                handler.flush()

            contents = Path(log_path).read_text(encoding="utf-8")

        console_output = console_stream.getvalue()
        self.assertIn("tick=7 event=test.info_event actor=tester", contents)
        self.assertIn("tick=7 event=test.warning_event actor=tester", contents)
        self.assertNotIn("test.info_event", console_output)
        self.assertIn("tick=7 event=test.warning_event actor=tester", console_output)

    def test_configure_logging_does_not_duplicate_handlers(self):
        from app.logging_config import configure_logging, reset_logging, LOG_NAMESPACE
        import logging

        self.addCleanup(reset_logging)

        console_stream = io.StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            configure_logging(
                log_dir=temp_dir,
                file_level="DEBUG",
                console_level="ERROR",
                console_stream=console_stream,
                reset=True,
            )
            logger = logging.getLogger(LOG_NAMESPACE)
            first_handler_count = len(logger.handlers)

            configure_logging(
                log_dir=temp_dir,
                file_level="INFO",
                console_level="WARNING",
                console_stream=console_stream,
                reset=True,
            )
            second_handler_count = len(logger.handlers)

        self.assertEqual(first_handler_count, 2)
        self.assertEqual(second_handler_count, 2)

    def test_logging_controls_default_levels_and_callbacks(self):
        from ui.controls import create_logging_controls

        fake_tk = FakeTkModule()
        parent = fake_tk.Frame()
        calls = []

        _frame, file_var, console_var = create_logging_controls(
            parent,
            on_file_change=lambda value: calls.append(("file", value)),
            on_console_change=lambda value: calls.append(("console", value)),
            tk_module=fake_tk,
        )

        self.assertEqual(file_var.get(), "INFO")
        self.assertEqual(console_var.get(), "WARNING")

        file_var.set("DEBUG")
        console_var.set("ERROR")

        self.assertIn(("file", "DEBUG"), calls)
        self.assertIn(("console", "ERROR"), calls)

    def test_logging_level_setters_update_file_and_console_levels_independently(self):
        from app.logging_config import (
            configure_logging,
            get_logging_levels,
            log_event,
            reset_logging,
            set_console_log_level,
            set_file_log_level,
        )
        from simulation import runtime

        self.addCleanup(reset_logging)

        with tempfile.TemporaryDirectory() as temp_dir:
            configure_logging(
                log_dir=temp_dir,
                file_level="INFO",
                console_level="WARNING",
                reset=True,
            )

            runtime.simulation_tick = 42
            log_event("INFO", "sim.debug", event="bot.test_event", bot="Bot0", mode="wander", reason="unit_test")
            set_file_log_level("DEBUG")
            levels = get_logging_levels()
            self.assertEqual(levels["file"], "DEBUG")
            self.assertEqual(levels["console"], "WARNING")

            set_console_log_level("ERROR")
            levels = get_logging_levels()
            self.assertEqual(levels["file"], "DEBUG")
            self.assertEqual(levels["console"], "ERROR")

            log_path = Path(temp_dir) / "simulation.log"
            contents = log_path.read_text(encoding="utf-8")
            self.assertIn("tick=42", contents)
            self.assertIn("event=bot.test_event", contents)
            self.assertNotIn("|", contents)

    def test_derive_bot_mode_uses_stable_priority_order(self):
        from robot.state_view import derive_bot_mode

        bot = self.make_bot()
        bot.battery = 0
        self.assertEqual(derive_bot_mode(bot), "depleted")

        bot.battery = 500
        bot.actively_charging = True
        self.assertEqual(derive_bot_mode(bot), "charging")

        bot.waiting_for_charger = True
        self.assertEqual(derive_bot_mode(bot), "waiting_for_charger")

        bot.brain.isOverlapping = True
        self.assertEqual(derive_bot_mode(bot), "overlap")

    def test_bot_keeps_charging_after_crossing_low_battery_threshold(self):
        canvas = DummyCanvas()
        charger = self.mod.Charger("Charger0")
        charger.centreX = 100
        charger.centreY = 100

        bot = self.make_bot()
        bot.x = 100
        bot.y = 100
        bot.theta = 0
        bot.sensorPositions = [100, 100, 100, 100]
        bot.battery = 604
        bot.charger = True
        bot.low_battery_active = True
        bot.target_charger = charger

        bot.update(canvas, [charger], 1.0)

        self.assertEqual(bot.battery, 613)
        self.assertTrue(bot.charger)
        self.assertTrue(bot.low_battery_active)
        self.assertTrue(charger.is_charging)
        self.assertIs(charger.charging_bot, bot)

    def test_remove_charger_clears_low_battery_bot_target_state(self):
        canvas = DummyCanvas()
        charger_a = self.mod.Charger("ChargerA")
        charger_b = self.mod.Charger("ChargerB")
        passive_objects = [charger_a, charger_b]
        chargers = [charger_a, charger_b]

        bot = self.make_bot()
        bot.battery = 500
        bot.low_battery_active = True
        bot.charger = True
        bot.path_calculated = True
        bot.target_charger = charger_b
        bot.path = deque([(10, 10)])

        updated_passive, updated_chargers = self.mod.remove_charger(
            canvas, passive_objects, chargers, [bot]
        )

        self.assertEqual(updated_chargers, [charger_a])
        self.assertNotIn(charger_b, updated_passive)
        self.assertIsNone(bot.target_charger)
        self.assertEqual(bot.path, deque())
        self.assertFalse(bot.path_calculated)
        self.assertFalse(bot.low_battery_active)
        self.assertFalse(bot.charger)

    def test_remove_bot_releases_charger_lock(self):
        canvas = DummyCanvas()
        charger = self.mod.Charger("Charger0")

        other_bot = self.make_bot("Bot0")
        charging_bot = self.make_bot("Bot1")
        charger.start_charging(charging_bot)

        remaining_agents = self.mod.remove_bot(canvas, [other_bot, charging_bot], [charger])

        self.assertEqual([agent.name for agent in remaining_agents], ["Bot0"])
        self.assertFalse(charger.is_charging)
        self.assertIsNone(charger.charging_bot)

    def test_collect_dirt_supports_basic_dirt_objects(self):
        canvas = DummyCanvas()
        bot = self.make_bot()
        bot.x = 50
        bot.y = 50

        counter = self.mod.Counter()
        dirt_obj = self.mod.dirt.Dirt("Dirt0", x=50, y=50)
        remaining = bot.collectDirt(canvas, [dirt_obj], counter, 0)

        self.assertEqual(remaining, [])
        self.assertEqual(counter.dirtCollected, 1)

    def test_lamp_signal_does_not_trigger_robot_avoidance(self):
        bot = self.make_bot()
        bot.sensorPositions = [100, 100, 100, 100]
        bot.brain.movingCount = 10
        lamp = self.mod.Lamp("Lamp0")
        lamp.centreX = 102
        lamp.centreY = 100

        bot.thinkAndAct([bot], [lamp])

        self.assertFalse(bot.brain.isAvoiding)
        self.assertFalse(bot.brain.isOverlapping)
        self.assertEqual((bot.sl, bot.sr), (5.0, 5.0))

    def test_depleted_bot_does_not_move_without_available_charge(self):
        canvas = DummyCanvas()
        bot = self.make_bot()
        bot.x = 100
        bot.y = 100
        bot.theta = 0
        bot.sl = 5
        bot.sr = 5
        bot.battery = 0

        before = (bot.x, bot.y)
        bot.update(canvas, [], 1.0)

        self.assertEqual(bot.battery, 0)
        self.assertEqual((bot.x, bot.y), before)
        self.assertEqual((bot.sl, bot.sr), (0.0, 0.0))

    def test_waiting_at_occupied_charger_with_empty_path_uses_slow_drain(self):
        canvas = DummyCanvas()
        charger = self.mod.Charger("Charger0")
        charger.centreX = 100
        charger.centreY = 100

        owner = self.make_bot("Owner")
        waiter = self.make_bot("Waiter")
        waiter.x = 100
        waiter.y = 100
        waiter.theta = 0
        waiter.sensorPositions = [100, 100, 100, 100]
        waiter.battery = 500
        waiter.charger = True
        waiter.low_battery_active = True
        waiter.target_charger = charger
        waiter.path = deque()

        charger.start_charging(owner)

        for _ in range(4):
            waiter.update(canvas, [charger], 1.0)
        self.assertEqual(waiter.battery, 500)
        self.assertEqual(waiter.wait_counter, 4)

        waiter.update(canvas, [charger], 1.0)
        self.assertEqual(waiter.battery, 499)
        self.assertEqual(waiter.wait_counter, 0)

    def test_module_execution_without_main_name_does_not_create_window(self):
        main_path = PROJECT_ROOT / "main.py"
        original_tk = tkinter.Tk
        tkinter_called = {"value": False}

        def fake_tk(*args, **kwargs):
            tkinter_called["value"] = True
            raise RuntimeError("tk should not be called")

        tkinter.Tk = fake_tk
        try:
            globals_dict = runpy.run_path(str(main_path), run_name="sim_import")
        finally:
            tkinter.Tk = original_tk

        self.assertFalse(tkinter_called["value"])
        self.assertIn("main", globals_dict)

    def test_reset_simulation_restores_pause_button_label(self):
        class DummyLabel:
            def __init__(self):
                self.calls = []

            def config(self, **kwargs):
                self.calls.append(kwargs)

        class DummyButton:
            def __init__(self):
                self.calls = []

            def config(self, **kwargs):
                self.calls.append(kwargs)

        class ResetCanvas(DummyCanvas):
            def after_cancel(self, *args, **kwargs):
                pass

            def winfo_width(self):
                return 1000

            def winfo_height(self):
                return 1000

        class FakeRoot:
            def resizable(self, *args, **kwargs):
                pass

        class FakeFrame:
            def winfo_toplevel(self):
                return FakeRoot()

        stats_vars = {
            key: DummyLabel()
            for key in ["collected", "debris", "active_bots", "avg_battery", "runtime", "cats_count", "chargers_count"]
        }
        pause_button = DummyButton()
        self.mod.simulation_running = False
        self.mod.after_id = None

        self.mod.reset_simulation(ResetCanvas(), FakeFrame(), stats_vars, None, pause_button)

        self.assertEqual(pause_button.calls[-1], {"text": "⏸ 暂停", "bg": "#e8a838"})

    def test_move_does_not_emit_numpy_matrix_deprecation_warning(self):
        canvas = DummyCanvas()
        bot = self.make_bot()
        bot.sl = 1.0
        bot.sr = 2.0

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            bot.move(canvas, 1.0)

        matrix_warnings = [w for w in caught if "matrix subclass" in str(w.message)]
        self.assertEqual(matrix_warnings, [])

    def test_astar_path_points_stay_within_canvas_bounds(self):
        astar = self.mod.AStar(1000, 1000, 20)

        path = astar.find_path(0, 0, 1000, 1000, [])

        self.assertLessEqual(max(x for x, _ in path), 1000)
        self.assertLessEqual(max(y for _, y in path), 1000)
        self.assertEqual(path[-1], (1000, 1000))

    def test_bot_keeps_approaching_occupied_charger_until_it_reaches_station(self):
        canvas = DummyCanvas()
        charger = self.mod.Charger("Charger0")
        charger.centreX = 200
        charger.centreY = 100

        owner = self.make_bot("Owner")
        waiter = self.make_bot("Waiter")
        waiter.x = 0
        waiter.y = 100
        waiter.theta = 0
        waiter.sensorPositions = [0, 100, 0, 100]
        waiter.battery = 500
        waiter.charger = True
        waiter.low_battery_active = True
        waiter.path_calculated = True
        waiter.target_charger = charger
        waiter.path = deque([(20, 100), (40, 100), (60, 100)])

        charger.start_charging(owner)

        before = (waiter.x, waiter.y)
        waiter.update(canvas, [charger], 1.0)

        self.assertNotEqual((waiter.x, waiter.y), before)
        self.assertNotEqual((waiter.sl, waiter.sr), (0.0, 0.0))

    def test_bot_replans_after_path_was_initially_blocked(self):
        canvas = DummyCanvas()
        charger = self.mod.Charger("Charger0")
        charger.centreX = 100
        charger.centreY = 100

        bot = self.make_bot()
        bot.x = 0
        bot.y = 100
        bot.theta = 0
        bot.sensorPositions = [0, 100, 0, 100]
        bot.battery = 500

        blockers = [
            self.mod.dirt.plusDirt("D0", x=80, y=100, trash_type="debris"),
            self.mod.dirt.plusDirt("D1", x=120, y=100, trash_type="debris"),
            self.mod.dirt.plusDirt("D2", x=100, y=80, trash_type="debris"),
            self.mod.dirt.plusDirt("D3", x=100, y=120, trash_type="debris"),
        ]

        bot.update(canvas, [charger] + blockers, 1.0)
        self.assertTrue(bot.path_calculated)
        self.assertEqual(bot.path, deque())

        # Expire the replan cooldown so the bot can retry
        bot.replan_cooldown = 0
        bot.update(canvas, [charger], 1.0)

        self.assertNotEqual(bot.path, deque())
        self.assertTrue(bot.charger)

    def test_low_battery_path_keeps_robot_clear_of_debris_obstacle(self):
        canvas = DummyCanvas()
        charger = self.mod.Charger("Charger0")
        charger.centreX = 100
        charger.centreY = 0

        blocker = self.mod.dirt.plusDirt("Blocker", x=100, y=100, trash_type="debris")

        bot = self.make_bot("Clearance")
        bot.x = 100
        bot.y = 200
        bot.theta = 0
        bot.sensorPositions = [100, 200, 100, 200]
        bot.battery = 500

        bot.update(canvas, [charger, blocker], 1.0)

        robot_clearance_radius = 30.0
        min_clearance = robot_clearance_radius + blocker.size

        self.assertNotEqual(bot.path, deque())
        self.assertTrue(
            all(
                math.dist((x, y), blocker.getLocation()) >= min_clearance
                for x, y in bot.path
            )
        )

    def test_straight_line_motion_scales_with_dt(self):
        canvas = DummyCanvas()
        bot = self.make_bot()
        bot.x = 0
        bot.y = 0
        bot.theta = 0
        bot.sl = 5
        bot.sr = 5

        bot.move(canvas, 2.0)

        self.assertEqual(bot.x, 10.0)
        self.assertEqual(bot.y, 0.0)

    def test_move_wraps_position_immediately_when_crossing_world_edge(self):
        canvas = DummyCanvas()
        bot = self.make_bot()
        bot.x = 998
        bot.y = 500
        bot.theta = 0
        bot.sl = 5
        bot.sr = 5

        bot.move(canvas, 1.0)

        self.assertEqual(bot.x, 0.0)
        self.assertEqual(bot.y, 500.0)

    def test_cat_motion_scales_with_dt(self):
        canvas = DummyCanvas()
        cat = self.mod.Cat("Cat0")
        cat.x = 100
        cat.y = 100
        cat.theta = 0
        cat.speed = 5
        cat.currentlyTurning = False
        cat.movingCount = 999

        cat.update(canvas, [], 2.0)

        self.assertEqual(cat.x, 110.0)
        self.assertEqual(cat.y, 100.0)

    def test_cat_turning_scales_with_dt(self):
        canvas = DummyCanvas()
        cat = self.mod.Cat("Cat0")
        cat.theta = 0
        cat.speed = 0
        cat.currentlyTurning = True
        cat.turningCount = 2

        cat.update(canvas, [], 2.0)

        self.assertAlmostEqual(cat.theta, -0.1)
        self.assertEqual(cat.turningCount, 1)

    def test_cat_avoidance_turning_scales_with_dt(self):
        canvas = DummyCanvas()
        cat = self.mod.Cat("Cat0")
        cat.x = 100
        cat.y = 100
        cat.theta = 0
        cat.speed = 0
        cat.isAvoiding = True
        cat.avoidCount = 2
        cat.avoidDirection = 1
        bot = self.make_bot()
        bot.x = 185
        bot.y = 100

        cat.update(canvas, [bot], 2.0)

        self.assertAlmostEqual(cat.theta, -0.2)
        self.assertEqual(cat.avoidCount, 1)

    def test_cat_avoidance_does_not_step_closer_to_bot_when_avoidance_starts(self):
        canvas = DummyCanvas()
        cat = self.mod.Cat("Cat0")
        cat.x = 100
        cat.y = 100
        cat.theta = 0
        cat.speed = 5

        bot = self.make_bot("Bot0")
        bot.x = 190
        bot.y = 100

        before = math.dist((cat.x, cat.y), (bot.x, bot.y))

        cat.update(canvas, [bot], 1.0)

        after = math.dist((cat.x, cat.y), (bot.x, bot.y))
        self.assertGreaterEqual(after, before)

    def test_cat_panics_and_jumps_before_collision_distance(self):
        canvas = DummyCanvas()
        cat = self.mod.Cat("Cat0")
        cat.x = 100
        cat.y = 100
        cat.theta = 0
        cat.speed = 0
        bot = self.make_bot("Bot0")
        bot.x = 170
        bot.y = 100

        cat.update(canvas, [bot], 1.0)

        self.assertTrue(cat.isJumping)
        self.assertGreater(math.dist((cat.x, cat.y), (100, 100)), 20)

    def test_cat_does_not_restart_panic_jump_while_already_jumping(self):
        canvas = DummyCanvas()
        cat = self.mod.Cat("Cat0")
        cat.x = 40
        cat.y = 100
        cat.theta = 0
        cat.speed = 0
        bot = self.make_bot("Bot0")
        bot.x = 80
        bot.y = 100

        with patch("entities.cat.random.uniform", side_effect=[0.0, 100.0, 0.5, 100.0]):
            cat.update(canvas, [bot], 1.0)
            first_jump_position = (cat.x, cat.y)
            first_jump_frames = cat.jump_frames

            cat.update(canvas, [bot], 1.0)

        self.assertGreaterEqual(
            math.hypot(cat._wrapped_delta(bot.x, first_jump_position[0]), cat._wrapped_delta(bot.y, first_jump_position[1])),
            cat.panic_distance,
        )
        self.assertEqual(first_jump_frames, 9)
        self.assertEqual(cat.x, first_jump_position[0])
        self.assertAlmostEqual(cat.y, first_jump_position[1])
        self.assertEqual(cat.jump_frames, 8)

    def test_cat_panic_jump_keeps_center_inside_visible_canvas_margin(self):
        canvas = DummyCanvas()
        cat = self.mod.Cat("Cat0")
        cat.x = 40
        cat.y = 40
        cat.theta = 0
        cat.speed = 0
        bot = self.make_bot("Bot0")
        bot.x = 90
        bot.y = 90

        with patch("entities.cat.random.uniform", side_effect=[0.0, 100.0]):
            cat.update(canvas, [bot], 1.0)

        self.assertGreaterEqual(cat.x, 120)
        self.assertGreaterEqual(cat.y, 120)
        self.assertLessEqual(cat.x, 880)
        self.assertLessEqual(cat.y, 880)

    def test_cat_jump_away_lands_inside_inner_field_bounds(self):
        cat = self.mod.Cat("Cat0")
        cat.x = 40
        cat.y = 500
        cat.theta = 0
        cat.speed = 0
        bot = self.make_bot("Bot0")
        bot.x = 90
        bot.y = 500

        with patch("entities.cat.random.uniform", side_effect=[0.0, 100.0]):
            cat.jump_away([bot])

        self.assertGreaterEqual(cat.x, 120)
        self.assertGreaterEqual(cat.y, 120)
        self.assertLessEqual(cat.x, 880)
        self.assertLessEqual(cat.y, 880)

    def test_cat_panic_jump_draw_stays_within_canvas_bounds(self):
        canvas = DummyCanvas()
        cat = self.mod.Cat("Cat0")
        cat.x = 40
        cat.y = 40
        cat.theta = 0
        cat.speed = 0
        bot = self.make_bot("Bot0")
        bot.x = 90
        bot.y = 90

        with patch("entities.cat.random.uniform", side_effect=[0.0, 100.0]):
            cat.update(canvas, [bot], 1.0)

        def iter_numbers(value):
            if isinstance(value, (int, float)):
                yield value
                return
            if isinstance(value, (list, tuple)):
                for item in value:
                    yield from iter_numbers(item)

        coords = []
        for _operation, args, _kwargs in canvas.operations:
            coords.extend(iter_numbers(args))

        self.assertGreaterEqual(min(coords), 0)
        self.assertLessEqual(max(coords), 1000)

    def test_cat_panics_across_wrapped_world_boundary_before_cross_edge_collision(self):
        canvas = DummyCanvas()
        cat = self.mod.Cat("Cat0")
        cat.x = 500
        cat.y = 996
        cat.theta = math.pi / 2
        cat.speed = 5
        bot = self.make_bot("Bot0")
        bot.x = 500
        bot.y = 20

        with patch("entities.cat.random.uniform", side_effect=[0.0, 100.0]):
            cat.update(canvas, [bot], 1.0)

        self.assertTrue(cat.isJumping)
        self.assertGreaterEqual(cat.x, 120)
        self.assertGreaterEqual(cat.y, 120)
        self.assertLessEqual(cat.x, 880)
        self.assertLessEqual(cat.y, 880)
        self.assertLess(cat.y, 996.0)
        self.assertGreaterEqual(
            math.hypot(cat._wrapped_delta(bot.x, cat.x), cat._wrapped_delta(bot.y, cat.y)),
            cat.panic_distance,
        )

    def test_cat_panic_jump_avoids_landing_on_another_bot(self):
        cat = self.mod.Cat("Cat0")
        cat.x = 500
        cat.y = 500
        cat.theta = 0
        cat.speed = 0

        nearest_bot = self.make_bot("Bot0")
        nearest_bot.x = 560
        nearest_bot.y = 500

        blocking_bot = self.make_bot("Bot1")
        blocking_bot.x = 400
        blocking_bot.y = 500

        with patch("entities.cat.random.uniform", side_effect=[0.0, 100.0]):
            cat.jump_away([nearest_bot, blocking_bot])

        self.assertTrue(cat.isJumping)

        distance_to_blocking_bot = math.hypot(
            cat._wrapped_delta(blocking_bot.x, cat.x),
            cat._wrapped_delta(blocking_bot.y, cat.y),
        )
        self.assertGreaterEqual(distance_to_blocking_bot, cat.panic_distance)

    def test_advance_simulation_frame_physically_freezes_bot_across_wrapped_blind_spot(self):
        from simulation import runtime
        from simulation.engine import advance_simulation_frame

        runtime.reset()
        canvas = DummyCanvas()
        bot = self.make_bot("Bot0")
        bot.x = 500
        bot.y = 20
        bot.theta = 0
        bot.battery = 1000
        bot.brain.currentlyTurning = False
        bot.brain.movingCount = 999
        bot.draw(canvas)

        cat = self.mod.Cat("Cat0")
        cat.x = 500
        cat.y = 996
        cat.theta = math.pi / 2
        cat.speed = 5

        original_update = bot.update
        update_entry_speeds = []

        def recording_update(canvas, passive_objects, dt):
            update_entry_speeds.append((bot.sl, bot.sr, bot.brain.is_cat_frozen, bot.brain.force_cat_freeze))
            return original_update(canvas, passive_objects, dt)

        bot.update = recording_update

        passive_objects, _snapshot = advance_simulation_frame(
            canvas,
            [bot],
            [],
            self.mod.Counter(),
            [cat],
            0,
            None,
            0.0,
            [],
            dt=1.0,
            now=1.0,
        )

        self.assertEqual(passive_objects, [])
        self.assertEqual(update_entry_speeds, [(0.0, 0.0, True, True)])
        self.assertEqual((bot.sl, bot.sr), (0.0, 0.0))
        self.assertAlmostEqual(bot.x, 500.0)
        self.assertAlmostEqual(bot.y, 20.0)
        self.assertFalse(bot.brain.is_cat_frozen)
        self.assertFalse(bot.brain.force_cat_freeze)

    def test_brain_avoids_cat_signal_instead_of_full_speed_forward(self):
        bot = self.make_bot()

        sl, sr, _new_x, _new_y = bot.brain.thinkAndAct(
            0,
            0,
            0,
            0,
            100,
            100,
            0,
            0,
            1000,
            catL=1500,
            catR=1500,
        )

        self.assertNotEqual((sl, sr), (5.0, 5.0))

    def test_brain_starts_cat_avoid_below_old_threshold_and_turns_in_place(self):
        bot = self.make_bot()

        sl, sr, _new_x, _new_y = bot.brain.thinkAndAct(
            0,
            0,
            0,
            0,
            100,
            100,
            0,
            0,
            1000,
            catL=450,
            catR=350,
        )

        self.assertTrue(bot.brain.isAvoidingCat)
        self.assertEqual((sl, sr), (3.0, -3.0))

    def test_brain_holds_cat_avoidance_for_minimum_frames_after_signal_disappears(self):
        bot = self.make_bot()

        bot.brain.thinkAndAct(
            0,
            0,
            0,
            0,
            100,
            100,
            0,
            0,
            1000,
            catL=1500,
            catR=1200,
        )
        self.assertTrue(bot.brain.isAvoidingCat)

        for _ in range(bot.brain.cat_avoid_hold_frames - 1):
            bot.brain.thinkAndAct(
                0,
                0,
                0,
                0,
                100,
                100,
                0,
                0,
                1000,
                catL=0,
                catR=0,
            )

        self.assertTrue(bot.brain.isAvoidingCat)

        bot.brain.thinkAndAct(
            0,
            0,
            0,
            0,
            100,
            100,
            0,
            0,
            1000,
            catL=0,
            catR=0,
        )

        self.assertFalse(bot.brain.isAvoidingCat)

    def test_brain_freezes_when_cat_signal_exceeds_close_range_threshold(self):
        bot = self.make_bot()

        sl, sr, _new_x, _new_y = bot.brain.thinkAndAct(
            0,
            0,
            0,
            0,
            100,
            100,
            0,
            0,
            1000,
            catL=1600,
            catR=1501,
        )

        self.assertTrue(bot.brain.is_cat_frozen)
        self.assertFalse(bot.brain.isAvoidingCat)
        self.assertEqual((sl, sr), (0.0, 0.0))

    def test_brain_releases_cat_freeze_and_resumes_normal_speed_after_cat_leaves(self):
        bot = self.make_bot()
        bot.brain.currentlyTurning = False
        bot.brain.movingCount = 999

        bot.brain.thinkAndAct(
            0,
            0,
            0,
            0,
            100,
            100,
            0,
            0,
            1000,
            catL=800,
            catR=600,
        )
        self.assertTrue(bot.brain.isAvoidingCat)

        bot.brain.thinkAndAct(
            0,
            0,
            0,
            0,
            100,
            100,
            0,
            0,
            1000,
            catL=1800,
            catR=1401,
        )
        self.assertTrue(bot.brain.is_cat_frozen)

        sl, sr, _new_x, _new_y = bot.brain.thinkAndAct(
            0,
            0,
            0,
            0,
            100,
            100,
            0,
            0,
            1000,
            catL=300,
            catR=300,
        )

        self.assertFalse(bot.brain.is_cat_frozen)
        self.assertFalse(bot.brain.isAvoidingCat)
        self.assertEqual((sl, sr), (5.0, 5.0))

    def test_brain_keeps_mid_range_cat_avoidance_without_triggering_freeze(self):
        bot = self.make_bot()

        sl, sr, _new_x, _new_y = bot.brain.thinkAndAct(
            0,
            0,
            0,
            0,
            100,
            100,
            0,
            0,
            1000,
            catL=1200,
            catR=900,
        )

        self.assertFalse(bot.brain.is_cat_frozen)
        self.assertTrue(bot.brain.isAvoidingCat)
        self.assertEqual((sl, sr), (3.0, -3.0))

    def test_moveit_does_not_double_apply_speed_multiplier(self):
        class FakeVar:
            def __init__(self, value):
                self.value = value

            def get(self):
                return self.value

        class FakeLabel:
            def __init__(self):
                self.text = None

            def config(self, **kwargs):
                self.text = kwargs.get("text", self.text)

        class FakeAgent:
            def __init__(self):
                self.name = "FakeBot"
                self.battery = 1000
                self.x = 100
                self.y = 100
                self.theta = 0
                self.sl = 0.0
                self.sr = 0.0
                self.received_dt = None
                self.received_cats = None

            def thinkAndAct(self, agents, passive_objects, cats=None):
                self.received_cats = cats

            def update(self, canvas, passive_objects, dt):
                self.received_dt = dt

            def collectDirt(self, canvas, passive_objects, count, debris_count, current_time=None):
                return passive_objects

            def draw(self, canvas):
                return None

        class FakeCat:
            def __init__(self):
                self.name = "FakeCat"
                self.x = 900
                self.y = 900
                self.received_dt = None

            def update(self, canvas, agents, dt, passiveObjects=()):
                self.received_dt = dt

        canvas = DummyCanvas()
        agent = FakeAgent()
        cat = FakeCat()
        speed_var = FakeVar(2.0)
        stats_vars = {
            "debris": FakeLabel(),
            "active_bots": FakeLabel(),
            "avg_battery": FakeLabel(),
            "cats_count": FakeLabel(),
            "chargers_count": FakeLabel(),
            "runtime": FakeLabel(),
            "collected": FakeLabel(),
        }

        self.mod.simulation_running = True
        self.mod.reset_flag = False
        self.mod.simulation_tick = 0

        self.mod.moveIt(
            canvas,
            [agent],
            [],
            self.mod.Counter(),
            [cat],
            0,
            stats_vars,
            time.time(),
            speed_var,
            object(),
            [],
            None,
        )

        self.assertEqual(agent.received_dt, 1.0)
        self.assertEqual(cat.received_dt, 1.0)
        self.assertEqual(canvas.after_calls[0][0], 25)
        self.assertEqual(agent.received_cats, [cat])

    def test_low_battery_bot_prefers_free_charger_over_nearer_occupied_one(self):
        canvas = DummyCanvas()
        occupied = self.mod.Charger("Occupied")
        occupied.centreX = 250
        occupied.centreY = 100
        occupied.start_charging(self.make_bot("Holder"))

        free = self.mod.Charger("Free")
        free.centreX = 400
        free.centreY = 100

        bot = self.make_bot("Seeker")
        bot.x = 100
        bot.y = 100
        bot.theta = 0
        bot.sensorPositions = [100, 100, 100, 100]
        bot.battery = 500

        bot.update(canvas, [occupied, free], 1.0)

        self.assertIs(bot.target_charger, free)

    def test_low_battery_bot_falls_back_to_farther_reachable_charger(self):
        canvas = DummyCanvas()
        blocked = self.mod.Charger("Blocked")
        blocked.centreX = 210
        blocked.centreY = 110

        reachable = self.mod.Charger("Reachable")
        reachable.centreX = 410
        reachable.centreY = 110

        blockers = [
            self.mod.dirt.plusDirt("B0", x=190, y=110, trash_type="debris"),
            self.mod.dirt.plusDirt("B1", x=230, y=110, trash_type="debris"),
            self.mod.dirt.plusDirt("B2", x=210, y=90, trash_type="debris"),
            self.mod.dirt.plusDirt("B3", x=210, y=130, trash_type="debris"),
        ]

        bot = self.make_bot("Fallback")
        bot.x = 100
        bot.y = 100
        bot.theta = 0
        bot.sensorPositions = [100, 100, 100, 100]
        bot.battery = 500

        bot.update(canvas, [blocked, reachable] + blockers, 1.0)

        self.assertIs(bot.target_charger, reachable)
        self.assertNotEqual(bot.path, deque())

    def test_bot_only_charges_from_one_nearby_charger_per_update(self):
        canvas = DummyCanvas()
        primary = self.mod.Charger("Primary")
        primary.centreX = 100
        primary.centreY = 100

        secondary = self.mod.Charger("Secondary")
        secondary.centreX = 120
        secondary.centreY = 100

        bot = self.make_bot("DualRange")
        bot.x = 100
        bot.y = 100
        bot.theta = 0
        bot.sensorPositions = [100, 100, 100, 100]
        bot.battery = 950
        bot.charger = True
        bot.low_battery_active = True
        bot.target_charger = primary

        bot.update(canvas, [primary, secondary], 1.0)

        self.assertEqual(bot.battery, 959)
        self.assertTrue(primary.is_charging)
        self.assertIs(primary.charging_bot, bot)
        self.assertFalse(secondary.is_charging)
        self.assertIsNone(secondary.charging_bot)

    def test_bot_stops_path_following_when_it_starts_charging_at_new_nearby_charger(self):
        canvas = DummyCanvas()
        nearby = self.mod.Charger("Nearby")
        nearby.centreX = 120
        nearby.centreY = 100

        far = self.mod.Charger("Far")
        far.centreX = 300
        far.centreY = 100

        bot = self.make_bot("Opportunist")
        bot.x = 100
        bot.y = 100
        bot.theta = 0
        bot.sensorPositions = [100, 100, 100, 100]
        bot.battery = 500
        bot.charger = True
        bot.low_battery_active = True
        bot.path_calculated = True
        bot.target_charger = far
        bot.path = deque([(200, 100)])

        bot.update(canvas, [nearby, far], 1.0)

        self.assertEqual(bot.x, 100.0)
        self.assertEqual(bot.y, 100.0)
        self.assertIs(bot.target_charger, nearby)
        self.assertEqual(bot.path, deque())
        self.assertTrue(nearby.is_charging)
        self.assertIs(nearby.charging_bot, bot)

    def test_bot_replans_when_current_target_becomes_occupied_and_other_free_charger_exists(self):
        canvas = DummyCanvas()
        occupied = self.mod.Charger("Occupied")
        occupied.centreX = 300
        occupied.centreY = 100
        occupied.start_charging(self.make_bot("Holder"))

        free = self.mod.Charger("Free")
        free.centreX = 220
        free.centreY = 220

        bot = self.make_bot("Switcher")
        bot.x = 100
        bot.y = 100
        bot.theta = 0
        bot.sensorPositions = [100, 100, 100, 100]
        bot.battery = 500
        bot.charger = True
        bot.low_battery_active = True
        bot.path_calculated = True
        bot.target_charger = occupied
        bot.path = deque([(150, 100), (200, 100), (250, 100)])

        bot.update(canvas, [occupied, free], 1.0)

        self.assertIs(bot.target_charger, free)
        self.assertNotEqual(bot.path, deque())

    def test_bot_replans_to_farther_free_charger_when_current_target_becomes_occupied(self):
        canvas = DummyCanvas()
        occupied = self.mod.Charger("Occupied")
        occupied.centreX = 220
        occupied.centreY = 100
        occupied.start_charging(self.make_bot("Holder"))

        farther_free = self.mod.Charger("FartherFree")
        farther_free.centreX = 420
        farther_free.centreY = 100

        bot = self.make_bot("FallbackTarget")
        bot.x = 100
        bot.y = 100
        bot.theta = 0
        bot.sensorPositions = [100, 100, 100, 100]
        bot.battery = 500
        bot.charger = True
        bot.low_battery_active = True
        bot.path_calculated = True
        bot.target_charger = occupied
        bot.path = deque([(150, 100), (200, 100)])

        bot.update(canvas, [occupied, farther_free], 1.0)

        self.assertIs(bot.target_charger, farther_free)
        self.assertNotEqual(bot.path, deque())

    def test_low_battery_overlap_still_triggers_separation_instead_of_path_following(self):
        canvas = DummyCanvas()
        charger = self.mod.Charger("Charger0")
        charger.centreX = 400
        charger.centreY = 100

        bots = [self.make_bot("BotA"), self.make_bot("BotB")]
        for bot in bots:
            bot.x = 100
            bot.y = 100
            bot.theta = 0
            bot.battery = 500
            bot.charger = True
            bot.low_battery_active = True
            bot.path_calculated = True
            bot.target_charger = charger
            bot.path = deque([(150, 100), (200, 100)])
            bot.draw(canvas)

        original_choice = self.mod.random.choice
        self.mod.random.choice = lambda seq: 1
        try:
            bots[0].thinkAndAct(bots, [charger])
            bots[0].update(canvas, [charger], 1.0)
        finally:
            self.mod.random.choice = original_choice

        self.assertTrue(bots[0].brain.isOverlapping)
        self.assertLess(bots[0].x, 100.0)

    def test_path_following_advances_to_next_waypoint_in_same_update(self):
        canvas = DummyCanvas()
        charger = self.mod.Charger("Far")
        charger.centreX = 300
        charger.centreY = 100

        bot = self.make_bot("Stepper")
        bot.x = 100
        bot.y = 100
        bot.theta = 0
        bot.sensorPositions = [100, 100, 100, 100]
        bot.battery = 500
        bot.charger = True
        bot.low_battery_active = True
        bot.path_calculated = True
        bot.target_charger = charger
        bot.path = deque([(100, 100), (130, 100)])

        bot.update(canvas, [charger], 1.0)

        self.assertEqual(bot.x, 103.0)
        self.assertEqual(bot.path, deque([(130, 100)]))

    def test_low_battery_path_following_does_not_oscillate_when_target_is_behind_bot(self):
        canvas = DummyCanvas()
        charger = self.mod.Charger("Behind")
        charger.centreX = 40
        charger.centreY = 100

        bot = self.make_bot("Turner")
        bot.x = 100
        bot.y = 100
        bot.theta = 0
        bot.sensorPositions = [100, 100, 100, 100]
        bot.battery = 500
        bot.charger = True
        bot.low_battery_active = True
        bot.path_calculated = True
        bot.target_charger = charger
        bot.path = deque([(40, 100)])

        start_position = (bot.x, bot.y)
        start_distance = bot.distanceTo(charger)

        for _ in range(80):
            bot.update(canvas, [charger], 1.0)

        self.assertNotEqual((bot.x, bot.y), start_position)
        self.assertLess(bot.distanceTo(charger), start_distance)

    def test_low_battery_path_following_turns_toward_waypoint_direction(self):
        canvas = DummyCanvas()
        charger = self.mod.Charger("North")
        charger.centreX = 100
        charger.centreY = 200

        bot = self.make_bot("HeadingFix")
        bot.x = 100
        bot.y = 100
        bot.theta = 0
        bot.sensorPositions = [100, 100, 100, 100]
        bot.battery = 500
        bot.charger = True
        bot.low_battery_active = True
        bot.path_calculated = True
        bot.target_charger = charger
        bot.path = deque([(100, 200)])

        bot.update(canvas, [charger], 1.0)

        self.assertGreater(bot.theta, 0.0)
        self.assertLess(bot.theta, math.pi)

    def test_bot_replans_to_newly_added_closer_free_charger(self):
        canvas = DummyCanvas()
        far = self.mod.Charger("Far")
        far.centreX = 400
        far.centreY = 100

        closer = self.mod.Charger("Closer")
        closer.centreX = 240
        closer.centreY = 100

        bot = self.make_bot("Adaptive")
        bot.x = 100
        bot.y = 100
        bot.theta = 0
        bot.sensorPositions = [100, 100, 100, 100]
        bot.battery = 500
        bot.charger = True
        bot.low_battery_active = True
        bot.path_calculated = True
        bot.target_charger = far
        bot.path = deque([(150, 100), (200, 100), (250, 100), (300, 100), (350, 100)])

        bot.update(canvas, [far, closer], 1.0)

        self.assertIs(bot.target_charger, closer)
        self.assertNotEqual(bot.path, deque())

    def test_bot_keeps_current_target_when_only_free_alternative_is_unreachable(self):
        class FakeAStar:
            def __init__(self):
                self.calls = []

            def find_path(self, start_x, start_y, target_x, target_y, passive_objects):
                self.calls.append((round(target_x), round(target_y)))
                if (round(target_x), round(target_y)) == (220, 220):
                    return None
                return [(start_x, start_y), (150, 100), (target_x, target_y)]

        canvas = DummyCanvas()
        occupied = self.mod.Charger("Occupied")
        occupied.centreX = 300
        occupied.centreY = 100
        occupied.start_charging(self.make_bot("Holder"))

        unreachable_free = self.mod.Charger("UnreachableFree")
        unreachable_free.centreX = 220
        unreachable_free.centreY = 220

        bot = self.make_bot("Persistent")
        bot.astar = FakeAStar()
        bot.x = 100
        bot.y = 100
        bot.theta = 0
        bot.sensorPositions = [100, 100, 100, 100]
        bot.battery = 500
        bot.charger = True
        bot.low_battery_active = True
        bot.path_calculated = True
        bot.target_charger = occupied
        original_path = deque([(150, 100), (200, 100), (250, 100)])
        bot.path = deque(original_path)

        bot.update(canvas, [occupied, unreachable_free], 1.0)

        self.assertIs(bot.target_charger, occupied)
        self.assertEqual(bot.path, original_path)

    def test_plus_dirt_can_be_cleaned_on_first_contact(self):
        canvas = DummyCanvas()
        bot = self.make_bot()
        bot.x = 50
        bot.y = 50
        counter = self.mod.Counter()
        dirt_obj = self.mod.dirt.plusDirt("Dust0", x=50, y=50, trash_type="dust")

        remaining = bot.collectDirt(canvas, [dirt_obj], counter, 0)

        self.assertEqual(remaining, [])
        self.assertEqual(counter.dirtCollected, 1)

    def test_liquid_cooldown_uses_shared_simulation_time(self):
        canvas = DummyCanvas()
        counter = self.mod.Counter()
        liquid = self.mod.dirt.plusDirt("Liquid0", x=50, y=50, trash_type="liquid")
        liquid.clean_count = 3

        newer_bot = self.make_bot("Newer")
        newer_bot.x = 50
        newer_bot.y = 50
        newer_bot.frame_counter = 0

        older_bot = self.make_bot("Older")
        older_bot.x = 50
        older_bot.y = 50
        older_bot.frame_counter = 99

        self.mod.simulation_tick = 1
        objs = newer_bot.collectDirt(canvas, [liquid], counter, 0)
        self.assertEqual(liquid.clean_count, 2)

        objs = older_bot.collectDirt(canvas, objs, counter, 0)
        self.assertEqual(liquid.clean_count, 2)
        self.assertEqual(counter.dirtCollected, 0)


if __name__ == "__main__":
    unittest.main()
