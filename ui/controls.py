import tkinter as tk

from app.logging_config import LOG_LEVEL_NAMES
from ui.theme import (
    ACCENT_BLUE,
    BG_CARD,
    BG_DARK,
    BTN_NEUTRAL_BG,
    BTN_NEUTRAL_FG,
    FONT_SECTION,
    FONT_SMALL,
    TEXT_ACCENT,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


def create_speed_controls(parent, tk_module=None):
    if tk_module is None:
        tk_module = tk

    frame = tk_module.Frame(parent, bg=BG_DARK)
    frame.pack(fill=tk_module.X, padx=8, pady=4)

    header = tk_module.Frame(frame, bg=BG_DARK)
    header.pack(fill=tk_module.X)
    tk_module.Label(header, text="仿真速度", fg=TEXT_PRIMARY, bg=BG_DARK, font=FONT_SMALL).pack(side=tk_module.LEFT)
    speed_label = tk_module.Label(header, text="1.0x", fg=ACCENT_BLUE, bg=BG_DARK, font=FONT_SECTION)
    speed_label.pack(side=tk_module.LEFT, padx=10)

    speed_var = tk_module.DoubleVar(value=1.0)
    speed_scale = tk_module.Scale(
        frame,
        from_=0.5,
        to=5.0,
        resolution=0.1,
        orient=tk_module.HORIZONTAL,
        variable=speed_var,
        bg=BG_DARK,
        fg=TEXT_PRIMARY,
        troughcolor=BG_CARD,
        highlightthickness=0,
        showvalue=False,
        length=220,
    )
    speed_scale.pack(fill=tk_module.X, pady=(2, 4))

    # Speed preset buttons
    preset_frame = tk_module.Frame(frame, bg=BG_DARK)
    preset_frame.pack(fill=tk_module.X)

    from ui.control_panel import RoundedButton

    presets = [("0.5x", 0.5), ("1x", 1.0), ("2x", 2.0), ("3x", 3.0), ("5x", 5.0)]
    for text, val in presets:
        btn = RoundedButton(
            preset_frame,
            text=text,
            bg_color=BTN_NEUTRAL_BG,
            fg_color=BTN_NEUTRAL_FG,
            font=FONT_SMALL,
            command=lambda v=val: speed_var.set(v),
            corner_radius=10,
            height=28,
        )
        btn.pack(side=tk_module.LEFT, expand=True, fill=tk_module.X, padx=2)

    def update_speed_label(*_args):
        speed_label.config(text=f"{speed_var.get():.1f}x")

    speed_var.trace_add("write", update_speed_label)
    return speed_var, speed_label


def create_brain_selector(parent, tk_module=None):
    if tk_module is None:
        tk_module = tk

    _DISPLAY_NAMES = {
        "subsumption": "Subsumption 包容式",
        "potential_field": "APF 人工势场法",
        "qlearning": "Q-Learning",
    }

    frame = tk_module.Frame(parent, bg=BG_DARK)
    frame.pack(fill=tk_module.X, padx=8, pady=4)

    header = tk_module.Frame(frame, bg=BG_DARK)
    header.pack(fill=tk_module.X)
    tk_module.Label(header, text="决策算法", fg=TEXT_PRIMARY, bg=BG_DARK, font=FONT_SMALL).pack(side=tk_module.LEFT)
    display_label = tk_module.Label(header, text=_DISPLAY_NAMES["subsumption"], fg=ACCENT_BLUE, bg=BG_DARK, font=FONT_SECTION)
    display_label.pack(side=tk_module.LEFT, padx=10)

    brain_type_var = tk_module.StringVar(value="subsumption")
    menu = tk_module.OptionMenu(frame, brain_type_var, "subsumption", "potential_field", "qlearning")
    menu.config(bg=BTN_NEUTRAL_BG, fg="#000000", font=FONT_SMALL, relief="flat", highlightthickness=0)
    menu.pack(fill=tk_module.X, pady=(2, 4))

    tk_module.Label(
        frame,
        text="⚠ 重置后生效",
        fg=TEXT_SECONDARY,
        bg=BG_DARK,
        font=("Helvetica", 8),
    ).pack(anchor="w")

    def _on_brain_change(*_args):
        display_label.config(text=_DISPLAY_NAMES.get(brain_type_var.get(), brain_type_var.get()))

    brain_type_var.trace_add("write", _on_brain_change)
    return brain_type_var


def create_logging_controls(
    parent,
    file_level="INFO",
    console_level="WARNING",
    on_file_change=None,
    on_console_change=None,
    tk_module=None,
):
    if tk_module is None:
        tk_module = tk

    frame = tk_module.Frame(parent, bg=BG_CARD)
    frame.pack(fill=tk_module.X, padx=8, pady=4)

    tk_module.Label(frame, text="日志设置", fg=TEXT_ACCENT, bg=BG_CARD, font=FONT_SMALL).pack(
        anchor="w", padx=6, pady=(4, 2),
    )

    row = tk_module.Frame(frame, bg=BG_CARD)
    row.pack(fill=tk_module.X, padx=6, pady=(0, 4))

    tk_module.Label(row, text="文件:", fg=TEXT_SECONDARY, bg=BG_CARD, font=FONT_SMALL).pack(side=tk_module.LEFT)
    file_var = tk_module.StringVar(value=file_level)
    file_other = [l for l in LOG_LEVEL_NAMES if l != file_level]
    file_menu = tk_module.OptionMenu(row, file_var, file_level, *file_other)
    file_menu.config(bg=BTN_NEUTRAL_BG, fg="#000000", font=FONT_SMALL, relief="flat", highlightthickness=0)
    file_menu.pack(side=tk_module.LEFT, padx=(2, 8))

    tk_module.Label(row, text="控制台:", fg=TEXT_SECONDARY, bg=BG_CARD, font=FONT_SMALL).pack(side=tk_module.LEFT)
    console_var = tk_module.StringVar(value=console_level)
    console_other = [l for l in LOG_LEVEL_NAMES if l != console_level]
    console_menu = tk_module.OptionMenu(row, console_var, console_level, *console_other)
    console_menu.config(bg=BTN_NEUTRAL_BG, fg="#000000", font=FONT_SMALL, relief="flat", highlightthickness=0)
    console_menu.pack(side=tk_module.LEFT, padx=2)

    if on_file_change is not None:
        file_var.trace_add("write", lambda *_args: on_file_change(file_var.get()))
    if on_console_change is not None:
        console_var.trace_add("write", lambda *_args: on_console_change(console_var.get()))

    return frame, file_var, console_var


def bind_keyboard_shortcuts(window, speed_var, pause_button, reset_callback, toggle_pause_fn):
    def key_handler(event):
        if event.keysym == "space":
            toggle_pause_fn(pause_button)
        elif event.keysym in {"r", "R"}:
            reset_callback()
        elif event.keysym in {"plus", "equal"}:
            speed_var.set(min(5.0, speed_var.get() + 0.1))
        elif event.keysym == "minus":
            speed_var.set(max(0.5, speed_var.get() - 0.1))

    window.bind("<Key>", key_handler)
