import math


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
        bot.x = 0
    elif bot.x < 0:
        bot.x = WORLD_SIZE - 1
    if bot.y >= WORLD_SIZE:
        bot.y = 0
    elif bot.y < 0:
        bot.y = WORLD_SIZE - 1


WORLD_SIZE = 1000


def _wrapped_delta(a, b):
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
    dx = _wrapped_delta(bot.x, xx)
    dy = _wrapped_delta(bot.y, yy)
    return math.sqrt(dx * dx + dy * dy)
