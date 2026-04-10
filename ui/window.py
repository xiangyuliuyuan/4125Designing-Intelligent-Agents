import tkinter as tk

from ui.theme import (
    BG_CANVAS,
    BG_DARK,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    SIDE_PANEL_WIDTH,
    WINDOW_TITLE,
)


def _configure_ttk_style():
    try:
        from tkinter import ttk
        style = ttk.Style()
        style.theme_use("clam")
    except Exception:
        pass


def _lock_toplevel_size(toplevel, defer=False):
    def _apply():
        try:
            toplevel.resizable(False, False)
        except AttributeError:
            pass

    if defer and hasattr(toplevel, "after_idle"):
        toplevel.after_idle(_apply)
    else:
        _apply()


def initialise(parent, tk_module=None):
    if tk_module is None:
        tk_module = tk

    canvas = tk_module.Canvas(parent, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg=BG_CANVAS, highlightthickness=0)
    canvas.pack(side=tk_module.LEFT)

    try:
        toplevel = parent.winfo_toplevel()
    except AttributeError:
        toplevel = parent
    # Real Tk windows are locked later in bootstrap after layout settles.
    # Applying resizable(False, False) here freezes the initial 1x1 geometry on macOS.
    if not hasattr(parent, "tk"):
        _lock_toplevel_size(toplevel)
    return canvas


def build_side_panel(parent, tk_module=None):
    if tk_module is None:
        tk_module = tk

    # 外层容器，固定宽度
    outer = tk_module.Frame(parent, bg=BG_DARK, width=SIDE_PANEL_WIDTH)
    outer.pack(side=tk_module.LEFT, fill="y")
    outer.pack_propagate(False)

    # 使用 Canvas + Frame 实现滚动，解决内容溢出时底部按钮不可见的问题
    scroll_canvas = tk_module.Canvas(
        outer, bg=BG_DARK, highlightthickness=0,
        width=SIDE_PANEL_WIDTH, yscrollincrement=2,
    )
    scroll_canvas.pack(side=tk_module.LEFT, fill="both", expand=True)

    inner_frame = tk_module.Frame(scroll_canvas, bg=BG_DARK)
    window_id = scroll_canvas.create_window((0, 0), window=inner_frame, anchor="nw")

    def _on_configure(_event):
        scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        # 保持内部 frame 宽度与 canvas 一致
        scroll_canvas.itemconfigure(window_id, width=scroll_canvas.winfo_width())

    inner_frame.bind("<Configure>", _on_configure)
    scroll_canvas.bind("<Configure>", lambda e: scroll_canvas.itemconfigure(window_id, width=e.width))

    # 绑定鼠标滚轮（macOS 用 <MouseWheel>）
    def _on_mousewheel(event):
        # macOS delta 通常为 ±1；乘以 15 配合 yscrollincrement=2，
        # 每次滚动约 30px，兼顾速度与流畅度
        if event.delta:
            delta = event.delta
            if abs(delta) > 10:  # Windows-style large delta
                delta = delta // 120 if delta != 0 else 0
            scroll_canvas.yview_scroll(int(-delta * 15), "units")
        elif event.num == 4:
            scroll_canvas.yview_scroll(-8, "units")
        elif event.num == 5:
            scroll_canvas.yview_scroll(8, "units")

    def _bind_wheel(_event=None):
        scroll_canvas.bind("<MouseWheel>", _on_mousewheel)
        inner_frame.bind("<MouseWheel>", _on_mousewheel)
        # Linux 支持
        scroll_canvas.bind("<Button-4>", lambda e: scroll_canvas.yview_scroll(-3, "units"))
        scroll_canvas.bind("<Button-5>", lambda e: scroll_canvas.yview_scroll(3, "units"))
        inner_frame.bind("<Button-4>", lambda e: scroll_canvas.yview_scroll(-3, "units"))
        inner_frame.bind("<Button-5>", lambda e: scroll_canvas.yview_scroll(3, "units"))

    def _unbind_wheel(_event=None):
        scroll_canvas.unbind("<MouseWheel>")
        inner_frame.unbind("<MouseWheel>")
        scroll_canvas.unbind("<Button-4>")
        scroll_canvas.unbind("<Button-5>")
        inner_frame.unbind("<Button-4>")
        inner_frame.unbind("<Button-5>")

    outer.bind("<Enter>", _bind_wheel)
    outer.bind("<Leave>", _unbind_wheel)

    return inner_frame


def create_main_window(tk_module=None):
    if tk_module is None:
        tk_module = tk

    window = tk_module.Tk()
    window.title(WINDOW_TITLE)
    window.configure(bg=BG_DARK)

    _configure_ttk_style()

    main_frame = tk_module.Frame(window, bg=BG_DARK)
    main_frame.pack(fill="both", expand=True)

    return window, main_frame
