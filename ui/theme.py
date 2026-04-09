"""Unified UI theme constants for the simulation."""

# ── Layout ──────────────────────────────────────────────
CANVAS_WIDTH = 1000
CANVAS_HEIGHT = 1000
SIDE_PANEL_WIDTH = 300
WINDOW_TITLE = "多智能体机器人仿真系统"

# ── Color palette ───────────────────────────────────────
BG_DARK = "#1e1e2e"
BG_PANEL = "#2a2a3d"
BG_CARD = "#353550"
BG_CANVAS = "#f8f8f0"

TEXT_PRIMARY = "#e0e0e8"
TEXT_SECONDARY = "#a0a0b8"
TEXT_ACCENT = "#7ec8e3"
TEXT_DARK = "#1e1e2e"

ACCENT_BLUE = "#5b9bd5"
ACCENT_GREEN = "#6bc96b"
ACCENT_ORANGE = "#e8a838"
ACCENT_RED = "#e85858"
ACCENT_PURPLE = "#a78bda"
ACCENT_CYAN = "#4ecdc4"
ACCENT_YELLOW = "#f0d060"

# Button colors
BTN_PRIMARY_BG = "#5b9bd5"
BTN_PRIMARY_FG = "#1e1e2e"
BTN_DANGER_BG = "#e85858"
BTN_DANGER_FG = "#1e1e2e"
BTN_SUCCESS_BG = "#6bc96b"
BTN_SUCCESS_FG = "#1e1e2e"
BTN_WARNING_BG = "#e8a838"
BTN_WARNING_FG = "#1e1e2e"
BTN_NEUTRAL_BG = "#555570"
BTN_NEUTRAL_FG = "#e0e0e8"

# Entity colors
BOT_COLOR_NORMAL = "#5b9bd5"
BOT_COLOR_CHARGING = "#6bc96b"
BOT_COLOR_AVOIDING = "#e8a838"
BOT_COLOR_DEPLETED = "#888888"
BOT_BODY_COLOR = "#d4af37"

CAT_COLOR_NORMAL = "#ff8c42"
CAT_COLOR_JUMPING = "#ff5555"

CHARGER_COLOR = "#888899"
CHARGER_CHARGING_OUTLINE = "#ff4444"
CHARGER_BOLT_COLOR = "#f0d060"

LAMP_COLOR = "#f0d060"
LAMP_GLOW_COLOR = "#fff8c0"

DIRT_COLORS = {
    "dust": "#c0c0c0",
    "crumb": "#8b6914",
    "paper": "#f0ead6",
    "liquid": "#7ec8e3",
    "hair": "#555555",
    "debris": "#aa4444",
}

# Battery bar
BATTERY_HIGH = "#6bc96b"
BATTERY_MID = "#e8a838"
BATTERY_LOW = "#e85858"
BATTERY_BG = "#333344"
BATTERY_MAX = 1000

# ── Fonts ───────────────────────────────────────────────
FONT_TITLE = ("Helvetica", 13, "bold")
FONT_SECTION = ("Helvetica", 11, "bold")
FONT_BODY = ("Helvetica", 10)
FONT_SMALL = ("Helvetica", 9)
FONT_TINY = ("Helvetica", 8)
FONT_MONO = ("Courier", 10)

# ── Entity status labels (Chinese) ─────────────────────
MODE_LABELS = {
    "wander": "巡逻",
    "charging": "充电中",
    "seeking_charger": "前往充电站",
    "avoid_bot": "避让机器人",
    "avoid_cat": "避让猫",
    "avoid_debris": "避让杂物",
    "overlap": "重叠",
    "depleted": "电量耗尽",
    "queuing": "排队等候",
    "waiting_for_charger": "等待充电",
    "path_following": "导航中",
    "panic_jump": "惊跳",
    "cat_freeze": "被猫吓住",
}
