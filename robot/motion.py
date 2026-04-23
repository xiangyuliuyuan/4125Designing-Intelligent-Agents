import math

WORLD_SIZE = 1000
BOT_RADIUS = 28  # matches the drawn body in bot.draw()
BOT_CONTACT_DISTANCE = 2 * BOT_RADIUS  # 56 px — bots may not come closer


def advance(bot, dt):
    if bot.sl == bot.sr:
        bot.x += bot.sr * dt * math.cos(bot.theta)
        bot.y += bot.sr * dt * math.sin(bot.theta)
    else:
        R = (bot.ll / 2.0) * ((bot.sr + bot.sl) / (bot.sl - bot.sr))
        omega = (bot.sl - bot.sr) / bot.ll
        ICCx = bot.x - R * math.sin(bot.theta)
        ICCy = bot.y + R * math.cos(bot.theta)
        newTheta = (bot.theta + omega * dt) % (2.0 * math.pi)
        bot.x = ICCx + R * math.sin(newTheta)
        bot.y = ICCy - R * math.cos(newTheta)
        bot.theta = newTheta


def wrap(bot):
    if bot.x >= WORLD_SIZE:
        bot.x -= WORLD_SIZE
    elif bot.x < 0:
        bot.x += WORLD_SIZE
    if bot.y >= WORLD_SIZE:
        bot.y -= WORLD_SIZE
    elif bot.y < 0:
        bot.y += WORLD_SIZE


def wrapped_delta(a, b):
    """Calculate shortest delta between two coordinates on a wrapping world."""
    delta = a - b
    half = WORLD_SIZE / 2
    if delta > half:
        delta -= WORLD_SIZE
    elif delta < -half:
        delta += WORLD_SIZE
    return delta


def distance_to(bot, obj):
    xx, yy = obj.getLocation()
    dx = wrapped_delta(bot.x, xx)
    dy = wrapped_delta(bot.y, yy)
    return math.sqrt(dx * dx + dy * dy)


def resolve_bot_collisions(bot, other_bots):
    """Post-move position correction: push `bot` out of any physical overlap
    with another bot so two bodies never occupy the same space.

    Runs *after* advance()/wrap() so the caller already has the candidate
    next position. Performed pairwise per bot — since the engine processes
    agents serially, a bot that enters this call already sees its
    neighbors' up-to-date positions for this frame.

    Works with the existing sensor-based avoidance: sensors steer early,
    this layer is the hard "you can't walk through another robot" floor.
    """
    for other in other_bots:
        if other is bot:
            continue
        dx = wrapped_delta(other.x, bot.x)
        dy = wrapped_delta(other.y, bot.y)
        dist_sq = dx * dx + dy * dy
        if dist_sq >= BOT_CONTACT_DISTANCE * BOT_CONTACT_DISTANCE:
            continue
        if dist_sq < 1e-6:
            # Exactly coincident (rare) — nudge along x so next frame's
            # vector is well-defined.
            bot.x = (bot.x + 1.0) % WORLD_SIZE
            continue
        dist = math.sqrt(dist_sq)
        overlap = BOT_CONTACT_DISTANCE - dist
        # Push bot AWAY from the other bot along the contact vector.
        bot.x -= (dx / dist) * overlap
        bot.y -= (dy / dist) * overlap
    wrap(bot)
