import os
import threading
import types
import unittest
import runpy
import tkinter
import time
import importlib
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
        self.overlapping_items = []
        self.tags_by_item = {}
        self.item_configs = {}
        self.last_scroll = None

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

    def create_window(self, *args, **kwargs):
        item_id = len(self.operations) + 1
        self.operations.append(("create_window", args, kwargs))
        return item_id

    def itemconfigure(self, item_id, **kwargs):
        self.item_configs[item_id] = dict(kwargs)
        self.operations.append(("itemconfigure", (item_id,), kwargs))

    def bbox(self, *args, **kwargs):
        return (0, 0, 1000, 1000)

    def yview_scroll(self, number, what):
        self.last_scroll = (number, what)

    def find_overlapping(self, *args, **kwargs):
        return tuple(self.overlapping_items)

    def gettags(self, item):
        return self.tags_by_item.get(item, ())

    def bind(self, *args, **kwargs):
        pass

    def after(self, delay, callback, *args):
        self.after_calls.append((delay, callback, args))
        return len(self.after_calls)

    def after_cancel(self, _after_id):
        pass


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
        self.tk = getattr(parent, "tk", None)

    def pack(self, *args, **kwargs):
        self.calls.append(("pack", args, kwargs))

    def config(self, **kwargs):
        self.kwargs.update(kwargs)
        self.calls.append(("config", kwargs))

    configure = config

    def cget(self, key):
        return self.kwargs.get(key, "")

    def bind(self, event, callback):
        self.calls.append(("bind", event, callback))

    def pack_propagate(self, flag):
        self.calls.append(("pack_propagate", flag))

    def winfo_width(self):
        return self.kwargs.get("width", 1000)

    def winfo_height(self):
        return self.kwargs.get("height", 1000)

    def winfo_class(self):
        return self.kwargs.get("widget_class", type(self).__name__)

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
        self.tk = self

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

    _RUNTIME_ATTRS = ("simulation_running", "reset_flag", "simulation_tick", "after_id")

    def setUp(self):
        self._saved_runtime = {
            attr: getattr(self.mod, attr, None)
            for attr in self._RUNTIME_ATTRS
            if hasattr(self.mod, attr)
        }

    def tearDown(self):
        for attr in self._RUNTIME_ATTRS:
            if attr in self._saved_runtime:
                setattr(self.mod, attr, self._saved_runtime[attr])
            elif hasattr(self.mod, attr):
                delattr(self.mod, attr)

    def make_bot(self, name="Bot0"):
        bot = self.mod.Bot(name)
        bot.setBrain(self.mod.Brain(bot))
        bot.setAStar(self.mod.AStar(1000, 1000, 20))
        return bot

    def exercise_bootstrap_callbacks(self, simulation_data=None, add_bot_impl=None, remove_bot_impl=None):
        from app import bootstrap
        from ui.stats_panel import set_initial_stats as real_set_initial_stats

        fake_tk = FakeTkModule()
        fake_window = fake_tk.Tk()
        fake_frame = fake_tk.Frame(fake_window)
        side_panel = fake_tk.Frame(fake_frame)
        canvas = DummyCanvas()
        speed_var = FakeTkVar(value=1.0)
        brain_var = FakeTkVar(value="subsumption")
        callback_store = {}
        pause_button = FakeTkWidget(side_panel, text="⏸ 暂停")
        reset_button = FakeTkWidget(side_panel, text="🔄 重置")
        stats_vars = {
            key: FakeTkWidget(side_panel, text="0")
            for key in ["collected", "debris", "active_bots", "avg_battery", "runtime", "cats_count", "chargers_count"]
        }

        if simulation_data is None:
            charger = self.mod.Charger("Charger0")
            charger.centreX = 300
            charger.centreY = 300
            bot = self.make_bot("Bot0")
            bot.battery = 1000
            simulation_data = {
                "agents": [bot],
                "passiveObjects": [charger],
                "count": self.mod.Counter(),
                "cats": [],
                "debris_count": 0,
                "chargers": [charger],
                "astar": self.mod.AStar(1000, 1000, 20),
                "start_time": time.time(),
            }

        if add_bot_impl is None:
            def add_bot_impl(_canvas, agents, _passive_objects, _astar, _chargers, **_kwargs):
                new_bot = self.make_bot(f"Bot{len(agents)}")
                agents.append(new_bot)
                return agents

        if remove_bot_impl is None:
            def remove_bot_impl(_canvas, agents, _chargers):
                if len(agents) > 1:
                    agents.pop()
                return agents

        def fake_set_initial_stats(stats_vars_arg, passive_objects, agents, cats, chargers, count, start_time, now=None):
            return real_set_initial_stats(stats_vars_arg, passive_objects, agents, cats, chargers, count, start_time, now=now)

        def capture_entity_controls(_parent, callbacks, tk_module=None):
            callback_store.update(callbacks)

        patchers = [
            patch.object(bootstrap, "configure_logging"),
            patch.object(bootstrap, "get_logging_levels", return_value={"file": "INFO", "console": "WARNING"}),
            patch.object(bootstrap, "create_main_window", return_value=(fake_window, fake_frame)),
            patch.object(bootstrap, "initialise", return_value=canvas),
            patch.object(bootstrap, "build_side_panel", return_value=side_panel),
            patch.object(bootstrap, "build_stats_panel", return_value=(fake_tk.Frame(side_panel), stats_vars)),
            patch.object(bootstrap, "create_speed_controls", return_value=(speed_var, FakeTkWidget(side_panel))),
            patch.object(bootstrap, "create_brain_selector", return_value=brain_var),
            patch.object(bootstrap, "create_simulation_data", return_value=simulation_data),
            patch.object(bootstrap, "_configure_qlearning_agents"),
            patch.object(bootstrap, "build_entity_controls", side_effect=capture_entity_controls),
            patch.object(bootstrap, "build_basic_controls", return_value=(fake_tk.Frame(side_panel), pause_button, reset_button)),
            patch.object(bootstrap, "create_logging_controls", return_value=(fake_tk.Frame(side_panel), FakeTkVar("INFO"), FakeTkVar("WARNING"))),
            patch.object(bootstrap, "set_initial_stats", side_effect=fake_set_initial_stats),
            patch.object(bootstrap, "CanvasTooltip", return_value=types.SimpleNamespace(update_data=lambda *args: None)),
            patch.object(bootstrap, "bind_keyboard_shortcuts"),
            patch.object(bootstrap, "schedule_simulation"),
            patch.object(bootstrap, "add_bot", side_effect=add_bot_impl),
            patch.object(bootstrap, "remove_bot", side_effect=remove_bot_impl),
        ]

        for patcher in patchers:
            patcher.start()
        for patcher in reversed(patchers):
            self.addCleanup(patcher.stop)

        bootstrap.run_app(tk_module=fake_tk)

        return {
            "brain_var": brain_var,
            "callbacks": callback_store,
            "stats_vars": stats_vars,
            "simulation_data": simulation_data,
        }

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
        from ui.window import create_main_window, initialise as window_initialise

        fake_tk = FakeTkModule()
        window, frame = create_main_window(tk_module=fake_tk)

        canvas = window_initialise(frame, tk_module=fake_tk)
        window.update_idletasks()
        size = window.geometry().split("+", 1)[0]
        width, height = map(int, size.split("x"))

        resizable_calls = [call for call in window.calls if call[0] == "resizable"]
        self.assertIsInstance(canvas, FakeTkCanvas)
        self.assertGreater(width, 100)
        self.assertGreater(height, 100)
        self.assertEqual(resizable_calls, [])

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

    def test_create_simulation_data_avoids_initial_actor_overlaps(self):
        from app.context import create_simulation_data
        import random

        random.seed(0)
        simulation_data = create_simulation_data(FakeTkCanvas(width=1000, height=1000))
        agents = simulation_data["agents"]
        cats = simulation_data["cats"]

        for index, bot in enumerate(agents):
            for other in agents[index + 1:]:
                self.assertGreaterEqual(math.hypot(bot.x - other.x, bot.y - other.y), 60.0)
            for cat in cats:
                self.assertGreaterEqual(bot.distanceTo(cat), 90.0)

    def test_add_bot_avoids_existing_agents_and_cats(self):
        from app.context import create_simulation_data
        from simulation.factory import add_bot
        import random

        random.seed(8)
        simulation_data = create_simulation_data(FakeTkCanvas(width=1000, height=1000))
        existing_agents = list(simulation_data["agents"])
        cats = simulation_data["cats"]

        updated_agents = add_bot(
            DummyCanvas(),
            simulation_data["agents"],
            simulation_data["passiveObjects"],
            simulation_data["astar"],
            simulation_data["chargers"],
            cats=cats,
        )

        new_bot = updated_agents[-1]
        for other in existing_agents:
            self.assertGreaterEqual(math.hypot(new_bot.x - other.x, new_bot.y - other.y), 60.0)
        for cat in cats:
            self.assertGreaterEqual(new_bot.distanceTo(cat), 90.0)

    def test_add_cat_avoids_existing_agents_and_cats(self):
        from app.context import create_simulation_data
        from simulation.factory import add_cat
        import random

        random.seed(11)
        simulation_data = create_simulation_data(FakeTkCanvas(width=1000, height=1000))
        existing_cats = list(simulation_data["cats"])
        agents = simulation_data["agents"]

        updated_cats = add_cat(
            DummyCanvas(),
            simulation_data["cats"],
            simulation_data["passiveObjects"],
            agents=agents,
        )

        new_cat = updated_cats[-1]
        for other in existing_cats:
            self.assertGreaterEqual(math.hypot(new_cat.x - other.x, new_cat.y - other.y), 40.0)
        for bot in agents:
            self.assertGreaterEqual(bot.distanceTo(new_cat), 90.0)

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

    def test_brain_selector_change_does_not_mix_brains_before_reset(self):
        recorded_brain_types = []
        initial_bot = self.make_bot("Bot0")
        initial_bot.battery = 1000
        charger = self.mod.Charger("Charger0")
        charger.centreX = 300
        charger.centreY = 300
        simulation_data = {
            "agents": [initial_bot],
            "passiveObjects": [charger],
            "count": self.mod.Counter(),
            "cats": [],
            "debris_count": 0,
            "chargers": [charger],
            "astar": self.mod.AStar(1000, 1000, 20),
            "start_time": time.time(),
        }

        def add_bot_impl(_canvas, agents, _passive_objects, _astar, _chargers, brain_type=None, **_kwargs):
            recorded_brain_types.append(brain_type)
            new_bot = self.make_bot(f"Bot{len(agents)}")
            agents.append(new_bot)
            return agents

        harness = self.exercise_bootstrap_callbacks(simulation_data=simulation_data, add_bot_impl=add_bot_impl)
        harness["brain_var"].set("qlearning")
        harness["callbacks"]["add_bot"]()

        self.assertEqual(recorded_brain_types, ["subsumption"])

    def test_add_bot_refreshes_avg_battery_immediately(self):
        initial_bot = self.make_bot("Bot0")
        initial_bot.battery = 1000
        charger = self.mod.Charger("Charger0")
        charger.centreX = 300
        charger.centreY = 300
        simulation_data = {
            "agents": [initial_bot],
            "passiveObjects": [charger],
            "count": self.mod.Counter(),
            "cats": [],
            "debris_count": 0,
            "chargers": [charger],
            "astar": self.mod.AStar(1000, 1000, 20),
            "start_time": time.time(),
        }

        def add_bot_impl(_canvas, agents, _passive_objects, _astar, _chargers, **_kwargs):
            new_bot = self.make_bot(f"Bot{len(agents)}")
            new_bot.battery = 500
            agents.append(new_bot)
            return agents

        harness = self.exercise_bootstrap_callbacks(simulation_data=simulation_data, add_bot_impl=add_bot_impl)
        harness["callbacks"]["add_bot"]()

        self.assertEqual(harness["stats_vars"]["active_bots"].cget("text"), "2")
        self.assertEqual(harness["stats_vars"]["avg_battery"].cget("text"), "750")

    def test_keyboard_shortcuts_ignore_focused_controls(self):
        from ui.controls import bind_keyboard_shortcuts

        window = FakeTkRoot()
        speed_var = FakeTkVar(value=1.0)
        toggle_calls = []
        reset_calls = []

        bind_keyboard_shortcuts(
            window,
            speed_var,
            pause_button=FakeTkWidget(),
            reset_callback=lambda: reset_calls.append("reset"),
            toggle_pause_fn=lambda _button: toggle_calls.append("toggle"),
        )

        _event_name, handler = window.bindings[0]
        focused_scale = types.SimpleNamespace(keysym="space", widget=types.SimpleNamespace(winfo_class=lambda: "Scale"))
        result = handler(focused_scale)

        self.assertEqual(toggle_calls, [])
        self.assertEqual(reset_calls, [])
        self.assertIsNone(result)

    def test_keyboard_shortcuts_return_break_for_handled_canvas_keys(self):
        from ui.controls import bind_keyboard_shortcuts

        window = FakeTkRoot()
        speed_var = FakeTkVar(value=1.0)
        toggle_calls = []

        bind_keyboard_shortcuts(
            window,
            speed_var,
            pause_button=FakeTkWidget(),
            reset_callback=lambda: None,
            toggle_pause_fn=lambda _button: toggle_calls.append("toggle"),
        )

        _event_name, handler = window.bindings[0]
        canvas_event = types.SimpleNamespace(keysym="space", widget=types.SimpleNamespace(winfo_class=lambda: "Canvas"))
        result = handler(canvas_event)

        self.assertEqual(toggle_calls, ["toggle"])
        self.assertEqual(result, "break")

    def test_tooltip_updates_text_and_position_when_hovering_same_entity(self):
        from ui.tooltip import CanvasTooltip

        canvas = DummyCanvas()
        canvas.overlapping_items = [1]
        canvas.tags_by_item = {1: ("Bot0",)}

        bot = self.make_bot("Bot0")
        bot.x = 10
        bot.y = 20
        bot.battery = 1000

        tooltip = CanvasTooltip(canvas, [bot], [], [])
        shown = []
        tooltip._show = lambda x, y, text: shown.append((x, y, text))

        tooltip._on_motion(types.SimpleNamespace(x=10, y=20, x_root=100, y_root=200))
        bot.battery = 900
        bot.x = 15
        bot.y = 25
        tooltip._on_motion(types.SimpleNamespace(x=15, y=25, x_root=110, y_root=210))

        self.assertEqual(len(shown), 2)
        self.assertEqual(shown[-1][0:2], (125, 220))
        self.assertIn("900", shown[-1][2])

    def test_tooltip_prefers_topmost_hovered_entity(self):
        from ui.tooltip import CanvasTooltip

        canvas = DummyCanvas()
        canvas.overlapping_items = [1, 2]
        canvas.tags_by_item = {
            1: ("Charger0",),
            2: ("BotX",),
        }

        charger = self.mod.Charger("Charger0")
        charger.centreX = 100
        charger.centreY = 100
        bot = self.make_bot("BotX")

        tooltip = CanvasTooltip(canvas, [bot], [], [charger])
        tag, info = tooltip._find_entity_from_items(canvas.overlapping_items)

        self.assertEqual(tag, "BotX")
        self.assertIn("BotX", info)

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

    def test_button_clicked_moves_only_nearest_bot(self):
        bot_a = self.make_bot("Bot0")
        bot_b = self.make_bot("Bot1")
        bot_c = self.make_bot("Bot2")
        bot_a.x, bot_a.y = 100, 100
        bot_b.x, bot_b.y = 300, 300
        bot_c.x, bot_c.y = 700, 700

        self.mod.buttonClicked(290, 295, [bot_a, bot_b, bot_c])

        self.assertEqual((bot_a.x, bot_a.y), (100, 100))
        self.assertEqual((bot_b.x, bot_b.y), (290, 295))
        self.assertEqual((bot_c.x, bot_c.y), (700, 700))

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

        self.assertEqual(bot.x, 3.0)
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

        # Subject is the yielder in the name-tiebreak (both bots are equally
        # low-battery, so name order decides). "BotZ" > "BotA_priority" so
        # BotZ yields and performs the overlap backup we're asserting on.
        bots = [self.make_bot("BotZ"), self.make_bot("BotA_priority")]
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

    def test_imported_main_runtime_aliases_proxy_reads_and_writes(self):
        from simulation import runtime

        runtime.reset()
        main_module = importlib.import_module("main")
        main_module = importlib.reload(main_module)

        self.assertTrue(main_module.simulation_running)
        runtime.simulation_tick = 12
        self.assertEqual(main_module.simulation_tick, 12)

        main_module.simulation_running = False
        self.assertFalse(runtime.simulation_running)

    def test_qlearning_end_episode_applies_terminal_reward_update(self):
        from robot.brain_qlearning import FORWARD, QLearningBrain

        bot = self.make_bot("Learner")
        brain = QLearningBrain(bot, alpha=0.1, gamma=0.95)
        brain.set_training(True)
        state = ("none", "none", "high", "low", "low", "low")
        brain.last_state = state
        brain.last_action = FORWARD
        brain.give_reward(10.0)

        brain.end_episode()

        self.assertAlmostEqual(brain.q_table[(state, FORWARD)], 1.0)
        self.assertEqual(brain.pending_reward, 0.0)

    def test_analyze_results_parses_current_qtable_key_format(self):
        import json

        from experiments.analyze_results import _parse_qtable

        with tempfile.TemporaryDirectory() as temp_dir:
            qtable_path = Path(temp_dir) / "qtable.json"
            qtable_path.write_text(
                json.dumps({
                    json.dumps([["left", "none", "high", "low", "low", "low"], 3]): 1.25,
                }),
                encoding="utf-8",
            )

            parsed = _parse_qtable(str(qtable_path))

        self.assertEqual(parsed[(("left", "none", "high", "low", "low", "low"), 3)], 1.25)

    def test_analyze_results_uses_current_qlearning_action_labels(self):
        from experiments import analyze_results

        self.assertEqual(
            analyze_results.ACTION_NAMES,
            [
                "FORWARD",
                "TURN_LEFT",
                "TURN_RIGHT",
                "SLOW_FORWARD",
                "SEEK_LIGHT_LEFT",
                "SEEK_LIGHT_RIGHT",
                "STOP",
            ],
        )

    def _assert_transition_counting(self, module, run_single_kwargs):
        """Verify that a runner module counts freeze/depletion transitions, not frames."""
        class StubAgent:
            def __init__(self):
                self.name = "Bot0"
                self.brain = types.SimpleNamespace(is_cat_frozen=False)
                self.battery = 100

        agent = StubAgent()

        def fake_create_simulation_data(_canvas, brain_type="subsumption", noOfCats=None, noOfBots=None):
            return {
                "agents": [agent],
                "passiveObjects": [],
                "count": types.SimpleNamespace(dirtCollected=0),
                "cats": [],
                "debris_count": 0,
                "chargers": [],
                "start_time": 0.0,
            }

        states = [
            (False, 100),
            (True, 0),
            (True, 0),
            (False, 0),
        ]

        def fake_advance(*args, **kwargs):
            frozen, battery = states.pop(0)
            agent.brain.is_cat_frozen = frozen
            agent.battery = battery
            return args[2], {}

        with patch.object(module, "create_simulation_data", side_effect=fake_create_simulation_data), \
             patch.object(module, "advance_simulation_frame", side_effect=fake_advance):
            result = module.run_single(**run_single_kwargs)

        self.assertEqual(result["cat_freeze_count"], 1)
        self.assertEqual(result["battery_depletions"], 1)

    def test_run_experiments_counts_freeze_and_depletion_transitions_not_frames(self):
        from experiments import run_experiments
        self._assert_transition_counting(
            run_experiments,
            {"brain_type": "subsumption", "seed": 0, "frames": 4},
        )

    def test_run_generalization_counts_freeze_and_depletion_transitions_not_frames(self):
        from experiments import run_generalization
        self._assert_transition_counting(
            run_generalization,
            {"brain_type": "subsumption", "seed": 0, "frames": 4, "config_name": "standard"},
        )

    def test_run_headless_qlearning_loads_default_qtable_when_none_provided(self):
        import json

        import run_headless
        from robot.brain_qlearning import QLearningBrain

        bot = self.mod.Bot("Bot0")
        bot.setBrain(QLearningBrain(bot))
        bot.setAStar(self.mod.AStar(1000, 1000, 20))
        world = ([bot], [], self.mod.Counter(), [], 0, [], 0.0)

        with tempfile.TemporaryDirectory() as temp_dir:
            qtable_path = Path(temp_dir) / "trained.json"
            qtable_path.write_text(
                json.dumps({
                    json.dumps([["left", "none", "high", "low", "low", "low"], 3]): 1.25,
                }),
                encoding="utf-8",
            )
            log_path = Path(temp_dir) / "headless.log"
            log_path.write_text("", encoding="utf-8")

            with patch.object(run_headless, "DEFAULT_QTABLE_PATH", str(qtable_path)), \
                 patch.object(run_headless, "initialise_world", return_value=world), \
                 patch.object(run_headless, "configure_logging", return_value=str(log_path)):
                result = run_headless.run_simulation(
                    seed=0,
                    frames=0,
                    emit_stdout=False,
                    brain_type="qlearning",
                )

        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(bot.brain.training)
        self.assertEqual(
            bot.brain.q_table[(("left", "none", "high", "low", "low", "low"), 3)],
            1.25,
        )

    def test_run_headless_qlearning_warns_when_qtable_missing(self):
        import run_headless
        from robot.brain_qlearning import QLearningBrain

        bot = self.mod.Bot("Bot0")
        bot.setBrain(QLearningBrain(bot))
        bot.setAStar(self.mod.AStar(1000, 1000, 20))
        world = ([bot], [], self.mod.Counter(), [], 0, [], 0.0)

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "headless.log"
            log_path.write_text("", encoding="utf-8")

            with patch.object(run_headless, "initialise_world", return_value=world), \
                 patch.object(run_headless, "configure_logging", return_value=str(log_path)), \
                 patch.object(run_headless.logger, "warning") as mock_warning:
                result = run_headless.run_simulation(
                    seed=0,
                    frames=0,
                    emit_stdout=False,
                    brain_type="qlearning",
                    qtable_path=str(Path(temp_dir) / "missing.json"),
                )

        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(len(bot.brain.q_table), 0)
        mock_warning.assert_called_once()
        self.assertIn("untrained random policy", mock_warning.call_args[0][0])

    def test_low_battery_subsumption_still_freezes_for_close_cat(self):
        bot = self.make_bot("Bot0")

        sl, sr, _new_x, _new_y = bot.brain.thinkAndAct(
            0, 0, 0, 0, 0, 0, 0, 0,
            500,
            0, 0, 0, 0,
            4000, 0,
        )

        self.assertEqual((sl, sr), (0.0, 0.0))
        self.assertTrue(bot.brain.is_cat_frozen)

    def test_low_battery_coverage_still_freezes_for_close_cat(self):
        from robot.brain_coverage import CoverageMapBrain

        bot = self.mod.Bot("Bot0")
        bot.setBrain(CoverageMapBrain(bot))
        bot.setAStar(self.mod.AStar(1000, 1000, 20))

        sl, sr, _new_x, _new_y = bot.brain.thinkAndAct(
            0, 0, 0, 0, 0, 0, 0, 0,
            500,
            0, 0, 0, 0,
            4000, 0,
        )

        self.assertEqual((sl, sr), (0.0, 0.0))
        self.assertTrue(bot.brain.is_cat_frozen)

    def test_count_transitions_counts_physical_cat_freeze_flag(self):
        from experiments.utils import count_transitions

        class StubAgent:
            def __init__(self):
                self.name = "Bot0"
                self.brain = types.SimpleNamespace(
                    is_cat_frozen=False,
                    force_cat_freeze=True,
                )
                self.battery = 100

        cat_freezes, battery_depletions, frozen_agents, depleted_agents = count_transitions(
            [StubAgent()],
            set(),
            set(),
        )

        self.assertEqual(cat_freezes, 1)
        self.assertEqual(battery_depletions, 0)
        self.assertEqual(frozen_agents, {"Bot0"})
        self.assertEqual(depleted_agents, set())

    def test_astar_prefers_wrapped_short_path_across_world_edge(self):
        astar = self.mod.AStar(1000, 1000, 20)

        path = astar.find_path(5, 500, 995, 500, [])

        self.assertIsNotNone(path)
        self.assertLess(len(path), 6)

    # ------------------------------------------------------------------
    # Bug fix regression tests
    # ------------------------------------------------------------------

    def test_qlearning_clears_cat_frozen_on_freeze_to_avoidance_transition(self):
        """Bug 1: is_cat_frozen must clear when cat_sum drops from freeze to avoidance range."""
        from robot.brain_qlearning import QLearningBrain

        bot = self.make_bot("Learner")
        brain = QLearningBrain(bot)
        bot.setBrain(brain)

        # Frame 1: cat_sum > 3000 -> freeze
        brain.thinkAndAct(0, 0, 0, 0, 500, 500, 0, 0, 800, 0, 0, 0, 0, 2000, 1500)
        self.assertTrue(brain.is_cat_frozen)

        # Frame 2: cat_sum in 700-3000 -> avoidance (not freeze)
        brain.thinkAndAct(0, 0, 0, 0, 500, 500, 0, 0, 800, 0, 0, 0, 0, 500, 400)
        self.assertFalse(brain.is_cat_frozen)
        self.assertTrue(brain.isAvoidingCat)

    def test_qlearning_overlap_does_not_emit_extra_backward_frame(self):
        """Bug 2: When overlap resolves, the bot should not output backward speeds."""
        from robot.brain_qlearning import QLearningBrain

        # Yielder needs a higher-priority neighbor in range. Name-tiebreak
        # makes "A_Priority" win, so our bot ("Z_Yielder") must back up.
        priority = self.make_bot("A_Priority")
        priority.x, priority.y = 510, 500  # close enough to be detected

        bot = self.make_bot("Z_Yielder")
        bot.x, bot.y = 500, 500
        bot._agents_ref = [bot, priority]
        brain = QLearningBrain(bot)
        bot.setBrain(brain)

        # Trigger overlap (bot is the yielder, should enter backing state)
        brain.thinkAndAct(0, 0, 0, 0, bot.x, bot.y, 0, 0, 800, 0, 0, 25000, 0, 0, 0)
        self.assertTrue(brain.isOverlapping)

        # Drain overlap counter
        for _ in range(14):
            brain.thinkAndAct(0, 0, 0, 0, bot.x, bot.y, 0, 0, 800, 0, 0, 25000, 0, 0, 0)

        # Frame after overlap resolves with no bot signal
        sl, sr, _, _ = brain.thinkAndAct(0, 0, 0, 0, bot.x, bot.y, 0, 0, 800, 0, 0, 0, 0, 0, 0)
        self.assertFalse(brain.isOverlapping)
        self.assertGreaterEqual(sl, 0.0, "Should not output backward speed after overlap resolves")

    def test_entity_names_unique_after_remove_and_add(self):
        """Bug 3: Entity names must stay unique across add/remove cycles."""
        from simulation.factory import add_cat, remove_cat, _reset_entity_counters, _entity_counters

        canvas = DummyCanvas()
        _reset_entity_counters()
        cats = []
        for i in range(4):
            from entities.cat import Cat
            cat = Cat(f"Cat{i}")
            cats.append(cat)
        _entity_counters["cat"] = 4

        remove_cat(canvas, cats)
        self.assertEqual(len(cats), 3)

        add_cat(canvas, cats)
        self.assertEqual(len(cats), 4)

        names = [c.name for c in cats]
        self.assertEqual(len(set(names)), len(names), f"Duplicate names found: {names}")

    def test_coverage_brain_logs_cat_freeze_transition(self):
        """Bug 4: CoverageMapBrain must log cat state transitions."""
        from unittest.mock import call
        from robot.brain_coverage import CoverageMapBrain

        bot = self.make_bot("CovBot")
        brain = CoverageMapBrain(bot)
        bot.setBrain(brain)

        with patch("robot.brain_coverage.log_event") as mock_log:
            # No cat -> freeze
            brain.thinkAndAct(0, 0, 0, 0, 500, 500, 0, 0, 800, 0, 0, 0, 0, 2000, 1500)
            freeze_calls = [c for c in mock_log.call_args_list if c[1].get("event") == "bot.cat_freeze_started"]
            self.assertEqual(len(freeze_calls), 1)

    def test_train_qlearning_zero_episodes_does_not_crash(self):
        """Bug 7: train() with episodes=0 must not raise UnboundLocalError."""
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "experiments/train_qlearning.py", "--episodes", "0", "--frames", "1"],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertNotIn("UnboundLocalError", result.stderr)

    def test_rq4_reward_training_zero_episodes_does_not_crash(self):
        """Bug 8: RQ4 train_with_reward() with --training-episodes 0 must not raise."""
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "experiments/run_rq4_rewards.py",
             "--training-episodes", "0", "--seeds", "1", "--frames", "1",
             "--reward-types", "baseline"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertNotIn("UnboundLocalError", result.stderr)

    def test_run_simulation_api_uses_pid_isolated_default_log(self):
        """Bug 11: Direct run_simulation() callers must not share headless.log."""
        import run_headless
        from robot.brain_qlearning import QLearningBrain

        bot = self.mod.Bot("Bot0")
        bot.setBrain(QLearningBrain(bot))
        bot.setAStar(self.mod.AStar(1000, 1000, 20))
        world = ([bot], [], self.mod.Counter(), [], 0, [], 0.0)

        captured = {}

        def fake_configure_logging(**kwargs):
            captured["log_filename"] = kwargs.get("log_filename")
            return "/tmp/unused.log"

        with patch.object(run_headless, "initialise_world", return_value=world), \
             patch.object(run_headless, "configure_logging", side_effect=fake_configure_logging), \
             patch.object(run_headless, "reset_headless_log_files"), \
             patch.object(run_headless, "count_events", return_value={
                 "collision_detected": 0, "cat.panic_jump": 0, "bot.physical_cat_freeze": 0,
             }):
            run_headless.run_simulation(seed=0, frames=0, emit_stdout=False)

        self.assertIsNotNone(captured["log_filename"])
        self.assertIn(str(os.getpid()), captured["log_filename"],
                      f"Default log must include PID, got {captured['log_filename']!r}")

    def test_run_simulation_concurrent_in_process_callers_isolated(self):
        """Bug 12: Concurrent threads calling run_simulation() must not share a log file
        and must not undercount events due to logger-state races."""
        import run_headless
        from concurrent.futures import ThreadPoolExecutor
        from robot.brain_qlearning import QLearningBrain

        captured_filenames = []
        captured_lock = threading.Lock()

        def make_fake_configure_logging():
            def fake_configure_logging(**kwargs):
                with captured_lock:
                    captured_filenames.append(kwargs.get("log_filename"))
                return "/tmp/unused.log"
            return fake_configure_logging

        def invoke():
            bot = self.mod.Bot("Bot0")
            bot.setBrain(QLearningBrain(bot))
            bot.setAStar(self.mod.AStar(1000, 1000, 20))
            world = ([bot], [], self.mod.Counter(), [], 0, [], 0.0)
            with patch.object(run_headless, "initialise_world", return_value=world), \
                 patch.object(run_headless, "configure_logging", side_effect=make_fake_configure_logging()), \
                 patch.object(run_headless, "reset_headless_log_files"), \
                 patch.object(run_headless, "count_events", return_value={
                     "collision_detected": 0, "cat.panic_jump": 0, "bot.physical_cat_freeze": 0,
                 }):
                return run_headless.run_simulation(seed=0, frames=0, emit_stdout=False)

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _i: invoke(), range(4)))

        self.assertEqual(len(captured_filenames), 4)
        self.assertEqual(len(set(captured_filenames)), 4,
                         f"Each concurrent call must get a unique filename; got {captured_filenames!r}")

    def test_count_events_tolerates_missing_log_file(self):
        """Bug 9: count_events must not crash when another process deleted the log."""
        from run_headless import count_events
        result = count_events("/tmp/nonexistent_log_path_for_test.log")
        self.assertEqual(result["collision_detected"], 0)
        self.assertEqual(result["cat.panic_jump"], 0)
        self.assertEqual(result["bot.physical_cat_freeze"], 0)

    def test_stats_snapshot_counts_cleanable_dirt_not_only_debris(self):
        """Bug 10: The '杂物剩余' stat must reflect dirt users add/remove/clean, not just debris."""
        from simulation.stats import build_snapshot
        from simulation.passive_index import invalidate_passive_object_index
        from entities import dirt as dirt_mod

        invalidate_passive_object_index()
        passive = [
            dirt_mod.plusDirt("D0", x=100, y=100, trash_type="dust"),
            dirt_mod.plusDirt("D1", x=200, y=200, trash_type="crumb"),
            dirt_mod.plusDirt("D2", x=300, y=300, trash_type="debris"),
        ]
        count = self.mod.Counter()
        snap = build_snapshot(passive, [], [], [], count, 0.0, now=0.0)
        self.assertEqual(snap["debris"], "3",
                         "Remaining trash should include cleanable dust/crumb AND debris")

    def test_bots_cannot_occupy_same_body_space(self):
        """Bug 15: physical non-penetration — two bots must never end a frame
        inside each other's body radius, regardless of what their brains say."""
        from robot.motion import BOT_CONTACT_DISTANCE, resolve_bot_collisions

        a = self.make_bot("A")
        b = self.make_bot("B")
        a.x, a.y = 500.0, 500.0
        b.x, b.y = 520.0, 500.0  # only 20 px apart — way inside contact
        resolve_bot_collisions(a, [b])
        # After correction, A must be at least the contact distance away.
        from robot.motion import wrapped_delta
        dx = wrapped_delta(b.x, a.x)
        dy = wrapped_delta(b.y, a.y)
        dist = (dx * dx + dy * dy) ** 0.5
        self.assertGreaterEqual(dist, BOT_CONTACT_DISTANCE - 1e-3,
                                f"bots still overlap after resolve: dist={dist}")

    def test_bot_move_blocks_penetration_into_stationary_bot(self):
        """Bug 15: a moving bot cannot walk through a stationary charging bot."""
        from robot.motion import BOT_CONTACT_DISTANCE, wrapped_delta
        canvas = DummyCanvas()

        stationary = self.make_bot("Charger-occupant")
        stationary.x, stationary.y = 500.0, 500.0
        stationary.sl = stationary.sr = 0.0

        mover = self.make_bot("Approacher")
        mover.x, mover.y = 450.0, 500.0  # 50 px away
        mover.theta = 0.0  # facing +x, directly at the stationary bot
        mover.sl = mover.sr = 5.0  # forward at full speed
        mover._agents_ref = [mover, stationary]

        # Step a handful of frames — mover should never end a frame inside the
        # stationary bot's body radius.
        for _ in range(20):
            mover.move(canvas, 1.0)
            dx = wrapped_delta(stationary.x, mover.x)
            dy = wrapped_delta(stationary.y, mover.y)
            dist = (dx * dx + dy * dy) ** 0.5
            self.assertGreaterEqual(dist, BOT_CONTACT_DISTANCE - 1e-3,
                                    f"mover penetrated stationary bot: dist={dist}")

    def test_bot_queues_when_another_seeker_is_closer_to_same_charger(self):
        """Bug 16: two low-battery bots targeting the same charger — the farther
        one must queue (stop) instead of racing in and dogpiling."""
        charger = types.SimpleNamespace(
            name="C0", centreX=500, centreY=500, is_charging=False,
            charging_bot=None, getLocation=lambda: (500, 500),
        )

        leader = self.make_bot("Leader")
        leader.target_charger = charger
        leader.charger = True
        leader.battery = 300
        leader.x, leader.y = 490.0, 500.0  # very close to the charger

        follower = self.make_bot("Follower")
        follower.target_charger = charger
        follower.charger = True
        follower.battery = 300
        follower.x, follower.y = 430.0, 500.0  # 70 px out — inside queue radius

        self.assertTrue(
            follower._should_queue_at_charger([leader, follower]),
            "follower should queue behind the closer seeker",
        )
        self.assertFalse(
            leader._should_queue_at_charger([leader, follower]),
            "leader is closest and charger is free — must not queue",
        )

    def test_right_of_way_breaks_head_on_symmetric_deadlock(self):
        """Bug 18: two bots facing each other must NOT both enter the overlap
        backing state — exactly one yields, the other continues."""
        from robot.brain import Brain

        # Two bots facing each other at the contact boundary. Same battery,
        # so priority comes from name tiebreak: "BotA" < "BotZ" → BotA wins.
        bot_a = self.make_bot("BotA")
        bot_a.x, bot_a.y = 500, 500
        bot_a.theta = 0.0  # facing +x (east)
        bot_a.setBrain(Brain(bot_a))

        bot_z = self.make_bot("BotZ")
        bot_z.x, bot_z.y = 556, 500
        bot_z.theta = 3.14159  # facing -x (west), toward bot_a
        bot_z.setBrain(Brain(bot_z))

        bot_a._agents_ref = [bot_a, bot_z]
        bot_z._agents_ref = [bot_a, bot_z]

        # Feed identical high bot-sensor signal to both (head-on encounter).
        overlap_sig = 25000
        bot_a.brain.thinkAndAct(0, 0, 0, 0, bot_a.x, bot_a.y, 0, 0, 800,
                                 0, 0, overlap_sig, 0, 0, 0)
        bot_z.brain.thinkAndAct(0, 0, 0, 0, bot_z.x, bot_z.y, 0, 0, 800,
                                 0, 0, overlap_sig, 0, 0, 0)

        # Exactly one must be in overlap backing mode (not both) — symmetry
        # broken.
        self.assertNotEqual(
            bot_a.brain.isOverlapping, bot_z.brain.isOverlapping,
            "Both bots entered overlap mode — symmetric deadlock",
        )
        self.assertTrue(bot_z.brain.isOverlapping,
                        "Higher-name bot (BotZ) should yield")
        self.assertFalse(bot_a.brain.isOverlapping,
                         "Lower-name bot (BotA) has priority, must not back up")

    def test_low_battery_bot_has_right_of_way_over_full_battery_bot(self):
        """Bug 18: a charger-seeking bot (low battery) must have priority
        over a cleaning bot (full battery) regardless of name order."""
        seeker = self.make_bot("BotZ_seeker")  # higher name, but low battery
        seeker.battery = 300
        cleaner = self.make_bot("BotA_cleaner")  # lower name, but full battery
        cleaner.battery = 900

        seeker.x, seeker.y = 500, 500
        cleaner.x, cleaner.y = 540, 500  # within RIGHT_OF_WAY_RADIUS
        seeker._agents_ref = [seeker, cleaner]
        cleaner._agents_ref = [seeker, cleaner]

        # Battery-class priority beats name tiebreak: seeker has right of way,
        # cleaner must yield even though its name is lexicographically smaller.
        self.assertFalse(seeker.should_yield_to_nearby_bots(),
                         "Low-battery seeker must not yield to a cleaner")
        self.assertTrue(cleaner.should_yield_to_nearby_bots(),
                        "Full-battery cleaner must yield to a low-battery seeker")

    def test_follower_still_waits_while_finished_bot_still_on_dock(self):
        """Bug 17: between stop_charging/reset_charging_state and the finished
        bot physically leaving, a follower must keep queuing (state-model gap
        between 'charger logically free' and 'dock physically occupied')."""
        from robot.motion import BOT_CONTACT_DISTANCE

        # Charger looks "free" in the logical sense.
        charger = types.SimpleNamespace(
            name="C0", centreX=500, centreY=500, is_charging=False,
            charging_bot=None, getLocation=lambda: (500, 500),
        )
        # Previous bot just finished charging: reset_charging_state() already
        # ran so target_charger is None and charger/actively_charging are
        # False -- but the bot is still physically sitting on the dock.
        finished = self.make_bot("Finished")
        finished.x, finished.y = 500.0, 500.0
        finished.target_charger = None
        finished.charger = False
        finished.actively_charging = False

        follower = self.make_bot("Follower")
        follower.target_charger = charger
        follower.charger = True
        follower.battery = 300
        follower.x, follower.y = 420.0, 500.0  # inside QUEUE_RADIUS

        # With finished bot inside BOT_CONTACT_DISTANCE of the charger,
        # the follower must queue despite all logical flags being cleared.
        self.assertLess(finished.distanceTo(charger), BOT_CONTACT_DISTANCE)
        self.assertTrue(
            follower._should_queue_at_charger([finished, follower]),
            "follower must keep queuing until the dock is physically clear",
        )

        # Once the finished bot drives clear of the dock, the follower
        # must resume approach (no permanent blocking).
        finished.x = 420.0  # >> BOT_CONTACT_DISTANCE from (500, 500)
        self.assertGreater(finished.distanceTo(charger), BOT_CONTACT_DISTANCE)
        self.assertFalse(
            follower._should_queue_at_charger([finished, follower]),
            "follower must resume once the dock is physically free",
        )

    def test_queue_radius_is_wider_than_docking_radius(self):
        """Bug 16: queue radius must be wider than the docking zone so the
        follower stops outside the dock instead of bumping the charger."""
        from robot.bot import Bot
        self.assertGreater(Bot.QUEUE_RADIUS, Bot.DOCKING_RADIUS,
                           "queue must start before the dock")
        self.assertGreaterEqual(Bot.QUEUE_RADIUS, 100,
                                "queue radius too tight to prevent dogpiles")

    def test_qlearning_respects_queuing_at_charger(self):
        """Bug 13: Q-learning bot must stop when queuing at a charger, not back-bump it."""
        from robot.brain_qlearning import QLearningBrain

        bot = self.make_bot("Queuer")
        brain = QLearningBrain(bot)
        bot.setBrain(brain)
        bot.queuing_at_charger = True

        # Strong bot_sum would normally trigger overlap and send bot flying.
        sl, sr, _, _ = brain.thinkAndAct(0, 0, 0, 0, 500, 500, 0, 0, 300,
                                          0, 0, 50000, 0, 0, 0)

        self.assertEqual((sl, sr), (0.0, 0.0),
                         "Queuing bot must stop even under overlap signal")

    def test_overlap_backup_displacement_is_bounded(self):
        """Bug 14: one overlap encounter must not send a bot flying ~75 px away."""
        from robot.brain import Brain

        bot = self.make_bot("Bumper")
        brain = Brain(bot)
        bot.setBrain(brain)

        # One overlap encounter: trigger with strong signal, then signal drops
        # to zero (as would happen once mutual backup separates the bots).
        total_displacement = 0.0
        for frame in range(30):
            bot_signal = 30000 if frame == 0 else 0
            sl, sr, _, _ = brain.thinkAndAct(
                0, 0, 0, 0, 500, 500, 0, 0, 800,
                0, 0, bot_signal, 0, 0, 0,
            )
            if sl < 0 and sr < 0:  # only count backward backup motion
                total_displacement += abs((sl + sr) / 2.0)

        # Previously: 15 frames @ speed 5 = 75 px. Must now be noticeably less.
        self.assertLess(total_displacement, 40.0,
                        f"Per-bot backup displacement too large: {total_displacement}")

    def test_cat_collides_with_debris_across_wrap_boundary(self):
        """Bug 6: Cat collision detection must use wrapped distance in toroidal world."""
        from entities.cat import Cat
        from entities import dirt as dirt_mod

        debris = dirt_mod.plusDirt("D0", x=998, y=500, trash_type="debris")
        debris.size = 12

        # Cat at x=4 -- unwrapped distance 994, wrapped distance 6 -> should collide
        self.assertTrue(Cat._collides_with_debris(4, 500, [debris]))

        # Cat at x=500 -- unwrapped distance 498, well beyond collision radius
        self.assertFalse(Cat._collides_with_debris(500, 500, [debris]))

    def test_coverage_find_least_visited_returns_nearest_unvisited(self):
        """Bug 5: Single-pass _find_least_visited_cell must find the nearest least-visited cell."""
        from robot.brain_coverage import CoverageMapBrain

        bot = self.make_bot("CovBot")
        brain = CoverageMapBrain(bot)
        bot.setBrain(brain)

        # Mark all cells as visited once
        for gy in range(50):
            for gx in range(50):
                brain.coverage_grid[gy][gx] = 1

        # Leave one cell at (1, 1) unvisited
        brain.coverage_grid[1][1] = 0

        result = brain._find_least_visited_cell(10, 10)
        self.assertEqual(result, (1, 1))


if __name__ == "__main__":
    unittest.main()
