import math

from robot.state_view import derive_bot_mode
from ui.theme import (
    BATTERY_BG,
    BATTERY_HIGH,
    BATTERY_LOW,
    BATTERY_MAX,
    BATTERY_MID,
    CAT_COLOR_JUMPING,
    CAT_COLOR_NORMAL,
    CHARGER_BOLT_COLOR,
    CHARGER_CHARGING_OUTLINE,
    CHARGER_COLOR,
    DIRT_COLORS,
    LAMP_COLOR,
    LAMP_GLOW_COLOR,
    MODE_LABELS,
    TEXT_DARK,
)

CAT_NORMAL_SIZE = 15
CAT_JUMP_SIZE = 18
CAT_JUMP_LANDING_MARGIN = 120
CAT_JUMP_HORIZONTAL_MARGIN = CAT_JUMP_LANDING_MARGIN
CAT_JUMP_TOP_MARGIN = CAT_JUMP_LANDING_MARGIN


# ── Bot rendering ───────────────────────────────────────

def _battery_color(battery):
    ratio = max(0.0, min(1.0, battery / BATTERY_MAX)) if BATTERY_MAX > 0 else 0.0
    if ratio > 0.5:
        return BATTERY_HIGH
    elif ratio > 0.2:
        return BATTERY_MID
    return BATTERY_LOW


def draw_bot_battery_bar(canvas, bot):
    bar_width = 40
    bar_height = 5
    bx = bot.x - bar_width / 2
    by = bot.y - 38

    canvas.create_rectangle(
        bx, by, bx + bar_width, by + bar_height,
        fill=BATTERY_BG, outline="", tags=bot.name,
    )
    battery = max(0, min(bot.battery, BATTERY_MAX))
    fill_width = max(0, bar_width * (battery / BATTERY_MAX))
    canvas.create_rectangle(
        bx, by, bx + fill_width, by + bar_height,
        fill=_battery_color(battery), outline="", tags=bot.name,
    )


def draw_bot_status_label(canvas, bot):
    mode = derive_bot_mode(bot)
    label = MODE_LABELS.get(mode, mode)
    canvas.create_text(
        bot.x, bot.y - 44,
        text=label,
        fill=_battery_color(bot.battery),
        font=("Helvetica", 10),
        tags=bot.name,
    )


def draw_bot_direction_arrow(canvas, bot):
    arrow_len = 38
    tip_x = bot.x + math.cos(bot.theta) * arrow_len
    tip_y = bot.y + math.sin(bot.theta) * arrow_len
    canvas.create_line(
        bot.x, bot.y, tip_x, tip_y,
        fill="#ffffff", width=2, arrow="last", arrowshape=(8, 10, 4),
        tags=bot.name,
    )


def draw_bot_path(canvas, bot):
    if bot.path:
        points = [bot.x, bot.y]
        for x, y in bot.path:
            points.extend([x, y])
        if len(points) >= 4:
            canvas.create_line(
                points, fill="#5b9bd5", width=1, dash=(4, 4),
                tags=bot.name,
            )


# ── Cat rendering ───────────────────────────────────────

def draw_cat(canvas, cat):
    if cat.isJumping:
        size = CAT_JUMP_SIZE
        color = CAT_COLOR_JUMPING
    else:
        size = CAT_NORMAL_SIZE
        color = CAT_COLOR_NORMAL

    # Body
    canvas.create_oval(
        cat.x - size, cat.y - size, cat.x + size, cat.y + size,
        fill=color, outline="#d07030", width=1, tags=cat.name,
    )

    # Ears
    ear_points = [
        (cat.x - 12, cat.y - size),
        (cat.x - 6, cat.y - size - 12),
        (cat.x, cat.y - size),
    ]
    canvas.create_polygon(ear_points, fill=color, outline="#d07030", tags=cat.name)
    ear_points_r = [
        (cat.x, cat.y - size),
        (cat.x + 6, cat.y - size - 12),
        (cat.x + 12, cat.y - size),
    ]
    canvas.create_polygon(ear_points_r, fill=color, outline="#d07030", tags=cat.name)

    # Inner ears
    canvas.create_polygon(
        [(cat.x - 10, cat.y - size), (cat.x - 6, cat.y - size - 8), (cat.x - 2, cat.y - size)],
        fill="#ffb0b0", tags=cat.name,
    )
    canvas.create_polygon(
        [(cat.x + 2, cat.y - size), (cat.x + 6, cat.y - size - 8), (cat.x + 10, cat.y - size)],
        fill="#ffb0b0", tags=cat.name,
    )

    # Eyes
    canvas.create_oval(cat.x - 7, cat.y - 5, cat.x - 2, cat.y + 1, fill="white", tags=cat.name)
    canvas.create_oval(cat.x + 2, cat.y - 5, cat.x + 7, cat.y + 1, fill="white", tags=cat.name)
    canvas.create_oval(cat.x - 6, cat.y - 4, cat.x - 3, cat.y - 1, fill="#2a2a3d", tags=cat.name)
    canvas.create_oval(cat.x + 3, cat.y - 4, cat.x + 6, cat.y - 1, fill="#2a2a3d", tags=cat.name)

    # Nose
    canvas.create_oval(cat.x - 2, cat.y + 1, cat.x + 2, cat.y + 3, fill="#ff9999", tags=cat.name)

    # Whiskers
    canvas.create_line(cat.x - 8, cat.y + 2, cat.x - 18, cat.y - 1, fill="#555", width=1, tags=cat.name)
    canvas.create_line(cat.x - 8, cat.y + 3, cat.x - 18, cat.y + 3, fill="#555", width=1, tags=cat.name)
    canvas.create_line(cat.x - 8, cat.y + 4, cat.x - 18, cat.y + 6, fill="#555", width=1, tags=cat.name)
    canvas.create_line(cat.x + 8, cat.y + 2, cat.x + 18, cat.y - 1, fill="#555", width=1, tags=cat.name)
    canvas.create_line(cat.x + 8, cat.y + 3, cat.x + 18, cat.y + 3, fill="#555", width=1, tags=cat.name)
    canvas.create_line(cat.x + 8, cat.y + 4, cat.x + 18, cat.y + 6, fill="#555", width=1, tags=cat.name)

    # Tail
    tail_points = [(cat.x - 12, cat.y + 10), (cat.x - 22, cat.y + 4), (cat.x - 20, cat.y + 14)]
    canvas.create_line(tail_points, fill=color, width=3, smooth=True, tags=cat.name)

    # Jump effect
    if cat.isJumping:
        canvas.create_text(
            cat.x, cat.y + size + 10,
            text="💨", font=("Helvetica", 10), tags=cat.name,
        )


# ── Charger rendering ──────────────────────────────────

def draw_charger(canvas, charger):
    cx, cy = charger.centreX, charger.centreY

    # Base platform
    canvas.create_rectangle(
        cx - 22, cy - 22, cx + 22, cy + 22,
        fill=CHARGER_COLOR, outline="#666677", width=1, tags=charger.name,
    )

    # Inner pad
    canvas.create_rectangle(
        cx - 14, cy - 14, cx + 14, cy + 14,
        fill="#555566", outline="", tags=charger.name,
    )

    # Lightning bolt symbol
    bolt_points = [cx - 3, cy - 10, cx + 5, cy - 2, cx + 1, cy - 2, cx + 3, cy + 10, cx - 5, cy + 2, cx - 1, cy + 2]
    canvas.create_polygon(bolt_points, fill=CHARGER_BOLT_COLOR, outline="", tags=charger.name)

    if charger.is_charging:
        # Glowing outline when charging
        canvas.create_rectangle(
            cx - 24, cy - 24, cx + 24, cy + 24,
            outline=CHARGER_CHARGING_OUTLINE, width=3, tags=charger.name,
        )
        # Charging indicator dots
        for i, offset in enumerate([-8, 0, 8]):
            canvas.create_oval(
                cx + offset - 2, cy + 26, cx + offset + 2, cy + 30,
                fill=CHARGER_CHARGING_OUTLINE, outline="", tags=charger.name,
            )


# ── Dirt rendering ──────────────────────────────────────

def draw_dirt(canvas, dirt_obj):
    trash_type = getattr(dirt_obj, "type", "dirt")
    if hasattr(dirt_obj, "size"):
        radius = max(2, min(15, int(dirt_obj.size)))
        color = DIRT_COLORS.get(trash_type, "#888888")
    else:
        radius = 2
        color = "#888888"

    cx, cy = dirt_obj.centreX, dirt_obj.centreY

    if trash_type == "paper":
        # Rectangle for paper
        canvas.create_rectangle(
            cx - radius, cy - radius * 0.7, cx + radius, cy + radius * 0.7,
            fill=color, outline="#ccccaa", tags=dirt_obj.name,
        )
    elif trash_type == "hair":
        # Curved line for hair
        canvas.create_line(
            cx - radius, cy, cx - radius / 2, cy - radius, cx + radius / 2, cy + radius, cx + radius, cy,
            fill=color, width=2, smooth=True, tags=dirt_obj.name,
        )
    elif trash_type == "liquid":
        # Blob shape for liquid
        canvas.create_oval(
            cx - radius - 2, cy - radius, cx + radius + 2, cy + radius,
            fill=color, outline="#5588aa", width=1, tags=dirt_obj.name,
        )
        if dirt_obj.clean_count != float("inf") and dirt_obj.clean_count > 0:
            canvas.create_text(
                cx, cy, text=str(dirt_obj.clean_count),
                fill=TEXT_DARK, font=("Helvetica", 10, "bold"), tags=dirt_obj.name,
            )
    elif trash_type == "debris":
        # X-marked obstacle
        canvas.create_rectangle(
            cx - radius, cy - radius, cx + radius, cy + radius,
            fill=color, outline="#882222", width=1, tags=dirt_obj.name,
        )
        canvas.create_line(cx - radius, cy - radius, cx + radius, cy + radius, fill="#ffffff", width=2, tags=dirt_obj.name)
        canvas.create_line(cx + radius, cy - radius, cx - radius, cy + radius, fill="#ffffff", width=2, tags=dirt_obj.name)
    else:
        # Default circle for dust/crumb
        canvas.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            fill=color, outline="", tags=dirt_obj.name,
        )


# ── Lamp rendering ──────────────────────────────────────

def draw_lamp(canvas, lamp):
    cx, cy = lamp.centreX, lamp.centreY

    # Outer glow
    canvas.create_oval(
        cx - 16, cy - 16, cx + 16, cy + 16,
        fill=LAMP_GLOW_COLOR, outline="", tags=lamp.name,
    )
    # Inner lamp
    canvas.create_oval(
        cx - 10, cy - 10, cx + 10, cy + 10,
        fill=LAMP_COLOR, outline="#c0b020", width=1, tags=lamp.name,
    )
    # Light rays
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x1 = cx + math.cos(rad) * 12
        y1 = cy + math.sin(rad) * 12
        x2 = cx + math.cos(rad) * 18
        y2 = cy + math.sin(rad) * 18
        canvas.create_line(x1, y1, x2, y2, fill="#e0d060", width=1, tags=lamp.name)
