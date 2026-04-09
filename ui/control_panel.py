import tkinter as tk

from ui.theme import (
    ACCENT_BLUE,
    ACCENT_GREEN,
    ACCENT_ORANGE,
    ACCENT_RED,
    BG_CARD,
    BG_DARK,
    BTN_NEUTRAL_BG,
    BTN_NEUTRAL_FG,
    BTN_PRIMARY_BG,
    BTN_PRIMARY_FG,
    BTN_WARNING_BG,
    BTN_WARNING_FG,
    FONT_BODY,
    FONT_SMALL,
)


# ── Canvas 圆角按钮 ──────────────────────────────────────
# tkinter 原生 Button 不支持 border-radius，用 Canvas 绘制圆角矩形模拟。
# 对外通过 config(text=..., bg=...) 兼容原有 pause_button.config() 调用。


class _CanvasShim:
    """轻量 Canvas 兼容层，供 fake-tk 测试环境使用。"""

    def __init__(self, parent=None, width=40, height=40, bg="white", **kwargs):
        self.parent = parent
        self.width = width
        self.height = height
        self.bg = bg
        self.kwargs = dict(kwargs)
        self.packed = False
        self._bindings = {}
        self._items = {}
        self._next_item_id = 1

    def pack(self, *args, **kwargs):
        self.packed = True

    def bind(self, event, callback):
        self._bindings[event] = callback

    def delete(self, *args, **kwargs):
        self._items.clear()

    def create_polygon(self, *args, **kwargs):
        item_id = self._next_item_id
        self._next_item_id += 1
        self._items[item_id] = {"type": "polygon", "args": args, "kwargs": kwargs}
        return item_id

    def create_text(self, *args, **kwargs):
        item_id = self._next_item_id
        self._next_item_id += 1
        self._items[item_id] = {"type": "text", "args": args, "kwargs": kwargs}
        return item_id

    def itemconfigure(self, item_id, **kwargs):
        if item_id in self._items:
            self._items[item_id]["kwargs"].update(kwargs)

    def config(self, **kwargs):
        self.kwargs.update(kwargs)

    configure = config

    def winfo_width(self):
        return self.width

    def winfo_height(self):
        return self.height

    def winfo_rgb(self, color):
        if isinstance(color, str) and color.startswith("#") and len(color) == 7:
            r = int(color[1:3], 16) * 257
            g = int(color[3:5], 16) * 257
            b = int(color[5:7], 16) * 257
            return r, g, b
        return 0, 0, 0

    def winfo_toplevel(self):
        if self.parent and hasattr(self.parent, "winfo_toplevel"):
            return self.parent.winfo_toplevel()
        return self.parent


class RoundedButton:
    """用 Canvas 绘制的圆角按钮，兼容 tk.Button 的 config(text=..., bg=...) 接口。"""

    def __init__(
        self,
        parent,
        text="",
        bg_color="#5b9bd5",
        fg_color="#1e1e2e",
        font=("Helvetica", 10),
        command=None,
        corner_radius=14,
        height=40,
        **kwargs,
    ):
        try:
            parent_bg = parent.cget("bg")
        except (AttributeError, tk.TclError):
            parent_bg = "#1e1e2e"
        if "width" not in kwargs:
            kwargs["width"] = 40

        canvas_kwargs = dict(kwargs)
        canvas_kwargs.update(
            {
                "highlightthickness": 0,
                "bg": parent_bg,
                "height": height,
                "cursor": "hand2",
            }
        )

        # Real Tk widgets need a master with `.tk`; fake-tk tests do not.
        if hasattr(parent, "tk"):
            self._canvas = tk.Canvas(parent, **canvas_kwargs)
        else:
            shim_kwargs = dict(canvas_kwargs)
            width = shim_kwargs.pop("width", 40)
            shim_height = shim_kwargs.pop("height", height)
            shim_bg = shim_kwargs.pop("bg", parent_bg)
            self._canvas = _CanvasShim(parent, width=width, height=shim_height, bg=shim_bg, **shim_kwargs)

        self.kwargs = {
            "text": text,
            "bg": bg_color,
            "fg": fg_color,
            "font": font,
            "command": command,
            "corner_radius": corner_radius,
            "height": height,
            **kwargs,
        }

        self._bg_color = bg_color
        self._fg_color = fg_color
        self._font = font
        self._command = command
        self._corner_radius = corner_radius
        self._btn_height = height
        self._text = text

        # 绘制占位（宽度会在 <Configure> 中确定）
        self._rect_id = None
        self._text_id = None

        self._canvas.bind("<Configure>", self._redraw)
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Enter>", self._on_enter)
        self._canvas.bind("<Leave>", self._on_leave)

    def __getattr__(self, name):
        return getattr(self._canvas, name)

    def pack(self, *args, **kwargs):
        return self._canvas.pack(*args, **kwargs)

    # ── 绘制 ──

    def _draw_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        """用 smooth polygon 绘制圆角矩形。"""
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return self._canvas.create_polygon(points, smooth=True, **kwargs)

    def _redraw(self, _event=None):
        self._canvas.delete("all")
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w < 2 or h < 2:
            return
        r = self._corner_radius
        self._rect_id = self._draw_rounded_rect(2, 2, w - 2, h - 2, r, fill=self._bg_color, outline="")
        self._text_id = self._canvas.create_text(w / 2, h / 2, text=self._text, fill=self._fg_color, font=self._font)

    # ── 交互 ──

    def _on_click(self, _event):
        if self._command:
            self._command()

    def _on_enter(self, _event):
        """鼠标悬停时略微提亮背景色。"""
        try:
            r, g, b = self._canvas.winfo_rgb(self._bg_color)
            # 每个通道是 0-65535，提亮 10%
            factor = 1.1
            r = min(65535, int(r * factor))
            g = min(65535, int(g * factor))
            b = min(65535, int(b * factor))
            hover_color = f"#{r >> 8:02x}{g >> 8:02x}{b >> 8:02x}"
            if self._rect_id:
                self._canvas.itemconfigure(self._rect_id, fill=hover_color)
        except Exception:
            pass

    def _on_leave(self, _event):
        if self._rect_id:
            self._canvas.itemconfigure(self._rect_id, fill=self._bg_color)

    # ── 兼容 tk.Button 的 config 接口 ──

    def config(self, **kwargs):
        """兼容 pause_button.config(text=..., bg=...) 的调用。"""
        changed = False
        if "text" in kwargs:
            self._text = kwargs.pop("text")
            self.kwargs["text"] = self._text
            changed = True
        if "bg" in kwargs:
            self._bg_color = kwargs.pop("bg")
            self.kwargs["bg"] = self._bg_color
            changed = True
        if "fg" in kwargs:
            self._fg_color = kwargs.pop("fg")
            self.kwargs["fg"] = self._fg_color
            changed = True
        # 其他参数传给父类
        if kwargs:
            if hasattr(self._canvas, "config"):
                self._canvas.config(**kwargs)
        if changed:
            self._redraw()

    # 同时兼容 configure（tkinter 的别名）
    configure = config


def _make_entity_group(parent, title, add_text, remove_text, add_cmd, remove_cmd, accent_color, tk_module):
    frame = tk_module.Frame(parent, bg=BG_CARD)
    frame.pack(fill=tk_module.X, padx=8, pady=3)

    lbl = tk_module.Label(frame, text=title, fg=accent_color, bg=BG_CARD, font=FONT_SMALL, anchor="w")
    lbl.pack(fill=tk_module.X, padx=6, pady=(4, 0))

    btn_row = tk_module.Frame(frame, bg=BG_CARD)
    btn_row.pack(fill=tk_module.X, padx=6, pady=(2, 6))

    add_btn = RoundedButton(
        btn_row,
        text=add_text,
        bg_color=accent_color,
        fg_color="#1e1e2e",
        font=FONT_SMALL,
        command=add_cmd,
        corner_radius=10,
        height=32,
    )
    add_btn.pack(side=tk_module.LEFT, padx=(0, 4), expand=True, fill=tk_module.X)

    rm_btn = RoundedButton(
        btn_row,
        text=remove_text,
        bg_color=BTN_NEUTRAL_BG,
        fg_color=BTN_NEUTRAL_FG,
        font=FONT_SMALL,
        command=remove_cmd,
        corner_radius=10,
        height=32,
    )
    rm_btn.pack(side=tk_module.LEFT, expand=True, fill=tk_module.X)

    return frame


def build_entity_controls(parent, callbacks, tk_module=None):
    if tk_module is None:
        tk_module = tk

    groups = [
        ("机器人", "➕ 添加", "➖ 移除", callbacks["add_bot"], callbacks["remove_bot"], ACCENT_BLUE),
        ("猫", "➕ 添加", "➖ 移除", callbacks["add_cat"], callbacks["remove_cat"], ACCENT_ORANGE),
        ("充电站", "➕ 添加", "➖ 移除", callbacks["add_charger"], callbacks["remove_charger"], ACCENT_GREEN),
        ("垃圾", "➕ 添加", "➖ 移除", callbacks["add_dirt"], callbacks["remove_dirt"], ACCENT_RED),
    ]

    frames = {}
    for title, add_text, rm_text, add_cmd, rm_cmd, color in groups:
        frames[title] = _make_entity_group(parent, title, add_text, rm_text, add_cmd, rm_cmd, color, tk_module)

    return frames


def build_basic_controls(parent, pause_command, reset_command, tk_module=None):
    if tk_module is None:
        tk_module = tk

    basic_frame = tk_module.Frame(parent, bg=BG_DARK)
    basic_frame.pack(fill=tk_module.X, padx=8, pady=4)

    # 使用 Canvas 圆角按钮替代原生 Button
    pause_button = RoundedButton(
        basic_frame,
        text="⏸ 暂停",
        bg_color=BTN_WARNING_BG,
        fg_color=BTN_WARNING_FG,
        font=FONT_BODY,
        command=pause_command,
        corner_radius=14,
        height=42,
    )
    pause_button.pack(fill=tk_module.X, pady=(0, 6))

    reset_button = RoundedButton(
        basic_frame,
        text="🔄 重置",
        bg_color=BTN_PRIMARY_BG,
        fg_color=BTN_PRIMARY_FG,
        font=FONT_BODY,
        command=reset_command,
        corner_radius=14,
        height=42,
    )
    reset_button.pack(fill=tk_module.X)

    return basic_frame, pause_button, reset_button
