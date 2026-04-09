"""Canvas tooltip for hovering over entities."""

import tkinter as tk

from robot.state_view import derive_bot_mode, derive_cat_mode
from ui.theme import BATTERY_MAX, BG_CARD, FONT_SMALL, MODE_LABELS, TEXT_PRIMARY


class CanvasTooltip:
    """Shows entity info on hover over canvas items."""

    def __init__(self, canvas, agents, cats, chargers):
        self.canvas = canvas
        self.agents = agents
        self.cats = cats
        self.chargers = chargers
        self._tip_window = None
        self._current_tag = None

        canvas.bind("<Motion>", self._on_motion)
        canvas.bind("<Leave>", self._hide)

    def update_data(self, agents, cats, chargers):
        self.agents = agents
        self.cats = cats
        self.chargers = chargers

    def _find_entity(self, tags):
        for tag in tags:
            for agent in self.agents:
                if agent.name == tag:
                    mode = derive_bot_mode(agent)
                    label = MODE_LABELS.get(mode, mode)
                    return (
                        f"🤖 {agent.name}\n"
                        f"状态: {label}\n"
                        f"电量: {agent.battery}/{BATTERY_MAX}\n"
                        f"位置: ({int(agent.x)}, {int(agent.y)})"
                    )
            for cat in self.cats:
                if cat.name == tag:
                    mode = derive_cat_mode(cat)
                    label = MODE_LABELS.get(mode, mode)
                    return (
                        f"🐱 {cat.name}\n"
                        f"状态: {label}\n"
                        f"位置: ({int(cat.x)}, {int(cat.y)})"
                    )
            for charger in self.chargers:
                if charger.name == tag:
                    charging_info = "空闲"
                    if charger.is_charging and charger.charging_bot:
                        charging_info = f"正在为 {charger.charging_bot.name} 充电"
                    return (
                        f"⚡ {charger.name}\n"
                        f"状态: {charging_info}\n"
                        f"位置: ({int(charger.centreX)}, {int(charger.centreY)})"
                    )
        return None

    def _on_motion(self, event):
        items = self.canvas.find_overlapping(event.x - 3, event.y - 3, event.x + 3, event.y + 3)
        if not items:
            self._hide()
            return

        all_tags = set()
        for item in items:
            all_tags.update(self.canvas.gettags(item))

        tag_key = frozenset(all_tags)
        if tag_key == self._current_tag:
            return

        info = self._find_entity(all_tags)
        if info:
            self._current_tag = tag_key
            self._show(event.x_root + 15, event.y_root + 10, info)
        else:
            self._hide()

    def _show(self, x, y, text):
        self._hide()
        self._tip_window = tw = tk.Toplevel(self.canvas)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        frame = tk.Frame(tw, bg=BG_CARD, padx=8, pady=6, relief="solid", bd=1)
        frame.pack()

        label = tk.Label(
            frame,
            text=text,
            fg=TEXT_PRIMARY,
            bg=BG_CARD,
            font=FONT_SMALL,
            justify="left",
        )
        label.pack()

    def _hide(self, event=None):
        self._current_tag = None
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None
