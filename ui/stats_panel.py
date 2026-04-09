import tkinter as tk

from simulation.stats import build_snapshot
from ui.theme import (
    ACCENT_BLUE,
    ACCENT_CYAN,
    ACCENT_GREEN,
    ACCENT_ORANGE,
    ACCENT_PURPLE,
    ACCENT_RED,
    ACCENT_YELLOW,
    BG_CARD,
    BG_DARK,
    FONT_SECTION,
    FONT_SMALL,
    FONT_TITLE,
    TEXT_ACCENT,
    TEXT_SECONDARY,
)


def _make_stat_card(parent, label_text, value_text, accent_color, tk_module):
    card = tk_module.Frame(parent, bg=BG_CARD)
    card.pack(fill=tk_module.X, padx=8, pady=2)

    lbl = tk_module.Label(card, text=label_text, fg=TEXT_SECONDARY, bg=BG_CARD, font=FONT_SMALL, anchor="w")
    lbl.pack(fill=tk_module.X, padx=6, pady=(4, 0))

    val = tk_module.Label(card, text=value_text, fg=accent_color, bg=BG_CARD, font=FONT_SECTION, anchor="w")
    val.pack(fill=tk_module.X, padx=6, pady=(0, 4))

    return val


def build_stats_panel(side_panel, tk_module=None):
    if tk_module is None:
        tk_module = tk

    stats_frame = tk_module.Frame(side_panel, bg=BG_DARK)
    stats_frame.pack(fill=tk_module.X, padx=4, pady=(8, 4))

    title = tk_module.Label(
        stats_frame,
        text="📊 仿真统计",
        fg=TEXT_ACCENT,
        bg=BG_DARK,
        font=FONT_TITLE,
        anchor="w",
    )
    title.pack(fill=tk_module.X, padx=8, pady=(0, 6))

    separator = tk_module.Frame(stats_frame, bg=ACCENT_BLUE, height=2)
    separator.pack(fill=tk_module.X, padx=8, pady=(0, 6))

    stats_vars = {
        "collected": _make_stat_card(stats_frame, "已收集垃圾", "0", ACCENT_GREEN, tk_module),
        "debris": _make_stat_card(stats_frame, "杂物剩余", "0", ACCENT_RED, tk_module),
        "active_bots": _make_stat_card(stats_frame, "活跃机器人", "0", ACCENT_BLUE, tk_module),
        "avg_battery": _make_stat_card(stats_frame, "平均电量", "0", ACCENT_YELLOW, tk_module),
        "runtime": _make_stat_card(stats_frame, "运行时间", "0s", ACCENT_CYAN, tk_module),
        "cats_count": _make_stat_card(stats_frame, "猫数量", "0", ACCENT_ORANGE, tk_module),
        "chargers_count": _make_stat_card(stats_frame, "充电站", "0", ACCENT_PURPLE, tk_module),
    }

    return stats_frame, stats_vars


def set_initial_stats(stats_vars, passive_objects, agents, cats, chargers, count, start_time, now=None):
    snapshot = build_snapshot(passive_objects, agents, cats, chargers, count, start_time, now=now)
    for key, value in snapshot.items():
        stats_vars[key].config(text=value)
