import os
import tkinter as tk

from app.context import apply_reset_result, create_simulation_data, schedule_simulation
from app.logging_config import (
    configure_logging,
    get_logging_levels,
    set_console_log_level,
    set_file_log_level,
)
from simulation import runtime
from simulation.engine import reset_simulation, toggle_pause
from simulation.factory import (
    add_bot,
    add_cat,
    add_charger,
    add_random_dirt_with_count,
    remove_bot,
    remove_cat,
    remove_charger,
    remove_dirt,
)
from ui.control_panel import build_basic_controls, build_entity_controls
from robot.brain_qlearning import QLearningBrain
from ui.controls import bind_keyboard_shortcuts, create_brain_selector, create_logging_controls, create_speed_controls
from ui.stats_panel import build_stats_panel, set_initial_stats
from ui.theme import ACCENT_BLUE, BG_DARK, FONT_SECTION, FONT_TITLE, TEXT_ACCENT, TEXT_SECONDARY
from ui.tooltip import CanvasTooltip
from ui.window import build_side_panel, create_main_window, initialise


_QTABLE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "experiments", "qtables", "trained.json")


def _configure_qlearning_agents(agents, brain_type):
    if brain_type == "qlearning" and os.path.exists(_QTABLE_PATH):
        for agent in agents:
            if hasattr(agent, "brain") and isinstance(agent.brain, QLearningBrain):
                agent.brain.load_qtable(_QTABLE_PATH)
                agent.brain.set_training(False)


def _add_section_header(parent, text):
    sep = tk.Frame(parent, bg=ACCENT_BLUE, height=1)
    sep.pack(fill=tk.X, padx=8, pady=(10, 2))
    lbl = tk.Label(parent, text=text, fg=TEXT_ACCENT, bg=BG_DARK, font=FONT_TITLE, anchor="w")
    lbl.pack(fill=tk.X, padx=8, pady=(0, 4))


def _add_keyboard_hint(parent):
    hints = "快捷键: 空格=暂停  R=重置  +/-=速度"
    lbl = tk.Label(parent, text=hints, fg=TEXT_SECONDARY, bg=BG_DARK, font=("Helvetica", 8), anchor="w")
    lbl.pack(fill=tk.X, padx=8, pady=(4, 4), side=tk.BOTTOM)


def run_app(tk_module=None):
    if tk_module is None:
        tk_module = tk

    configure_logging()

    window, main_frame = create_main_window(tk_module=tk_module)

    # Left: Canvas
    canvas = initialise(main_frame, tk_module=tk_module)

    # Right: Side panel
    side_panel = build_side_panel(main_frame, tk_module=tk_module)

    # ── Stats section ──
    _, stats_vars = build_stats_panel(side_panel, tk_module=tk_module)

    # ── Controls section ──
    _add_section_header(side_panel, "🎮 控制面板")

    speed_var, _speed_label = create_speed_controls(side_panel, tk_module=tk_module)

    brain_type_var = create_brain_selector(side_panel, tk_module=tk_module)

    simulation_data = create_simulation_data(canvas, brain_type=brain_type_var.get())
    _configure_qlearning_agents(simulation_data["agents"], brain_type_var.get())

    def add_bot_callback():
        simulation_data["agents"] = add_bot(
            canvas,
            simulation_data["agents"],
            simulation_data["passiveObjects"],
            simulation_data["astar"],
            simulation_data["chargers"],
            brain_type=brain_type_var.get(),
        )
        _configure_qlearning_agents(simulation_data["agents"][-1:], brain_type_var.get())
        stats_vars["active_bots"].config(text=str(len(simulation_data["agents"])))
        tooltip.update_data(simulation_data["agents"], simulation_data["cats"], simulation_data["chargers"])

    def remove_bot_callback():
        simulation_data["agents"] = remove_bot(
            canvas,
            simulation_data["agents"],
            simulation_data["chargers"],
        )
        stats_vars["active_bots"].config(text=str(len(simulation_data["agents"])))
        tooltip.update_data(simulation_data["agents"], simulation_data["cats"], simulation_data["chargers"])

    def add_cat_callback():
        simulation_data["cats"] = add_cat(canvas, simulation_data["cats"], simulation_data["passiveObjects"])
        stats_vars["cats_count"].config(text=str(len(simulation_data["cats"])))
        tooltip.update_data(simulation_data["agents"], simulation_data["cats"], simulation_data["chargers"])

    def remove_cat_callback():
        simulation_data["cats"] = remove_cat(canvas, simulation_data["cats"])
        stats_vars["cats_count"].config(text=str(len(simulation_data["cats"])))
        tooltip.update_data(simulation_data["agents"], simulation_data["cats"], simulation_data["chargers"])

    def add_charger_callback():
        simulation_data["passiveObjects"], simulation_data["chargers"] = add_charger(
            canvas,
            simulation_data["passiveObjects"],
            simulation_data["chargers"],
        )
        stats_vars["chargers_count"].config(text=str(len(simulation_data["chargers"])))
        tooltip.update_data(simulation_data["agents"], simulation_data["cats"], simulation_data["chargers"])

    def remove_charger_callback():
        simulation_data["passiveObjects"], simulation_data["chargers"] = remove_charger(
            canvas,
            simulation_data["passiveObjects"],
            simulation_data["chargers"],
            simulation_data["agents"],
        )
        stats_vars["chargers_count"].config(text=str(len(simulation_data["chargers"])))
        tooltip.update_data(simulation_data["agents"], simulation_data["cats"], simulation_data["chargers"])

    def add_dirt_callback():
        simulation_data["passiveObjects"] = add_random_dirt_with_count(
            canvas,
            simulation_data["passiveObjects"],
            stats_vars["debris"],
            stats_vars,
        )

    def remove_dirt_callback():
        simulation_data["passiveObjects"] = remove_dirt(canvas, simulation_data["passiveObjects"], stats_vars)

    callbacks = {
        "add_bot": add_bot_callback,
        "remove_bot": remove_bot_callback,
        "add_cat": add_cat_callback,
        "remove_cat": remove_cat_callback,
        "add_charger": add_charger_callback,
        "remove_charger": remove_charger_callback,
        "add_dirt": add_dirt_callback,
        "remove_dirt": remove_dirt_callback,
    }

    _add_section_header(side_panel, "🏗 实体管理")
    build_entity_controls(side_panel, callbacks, tk_module=tk_module)

    def reset_callback():
        result = reset_simulation(canvas, main_frame, stats_vars, speed_var, pause_button, brain_type=brain_type_var.get())
        if result:
            apply_reset_result(simulation_data, result)
            _configure_qlearning_agents(simulation_data["agents"], brain_type_var.get())
            tooltip.update_data(simulation_data["agents"], simulation_data["cats"], simulation_data["chargers"])

            schedule_simulation(
                canvas,
                simulation_data,
                stats_vars,
                speed_var,
                pause_button,
            )

    _add_section_header(side_panel, "⚙ 操作")
    _basic_frame, pause_button, _reset_button = build_basic_controls(
        side_panel,
        pause_command=lambda: toggle_pause(pause_button),
        reset_command=reset_callback,
        tk_module=tk_module,
    )

    current_levels = get_logging_levels()
    create_logging_controls(
        side_panel,
        file_level=current_levels["file"] or "INFO",
        console_level=current_levels["console"] or "WARNING",
        on_file_change=set_file_log_level,
        on_console_change=set_console_log_level,
        tk_module=tk_module,
    )

    _add_keyboard_hint(side_panel)

    set_initial_stats(
        stats_vars,
        simulation_data["passiveObjects"],
        simulation_data["agents"],
        simulation_data["cats"],
        simulation_data["chargers"],
        simulation_data["count"],
        simulation_data["start_time"],
        now=simulation_data["start_time"],
    )

    tooltip = CanvasTooltip(
        canvas,
        simulation_data["agents"],
        simulation_data["cats"],
        simulation_data["chargers"],
    )

    bind_keyboard_shortcuts(window, speed_var, pause_button, reset_callback, toggle_pause)
    schedule_simulation(canvas, simulation_data, stats_vars, speed_var, pause_button)

    window.update_idletasks()
    window.resizable(False, False)

    window.mainloop()
