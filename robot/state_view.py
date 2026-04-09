def derive_bot_mode(bot):
    brain = getattr(bot, "brain", None)

    if brain and getattr(brain, "isOverlapping", False):
        return "overlap"
    if getattr(bot, "battery", 1) <= 0:
        return "depleted"
    if getattr(bot, "queuing_at_charger", False):
        return "queuing"
    if getattr(bot, "waiting_for_charger", False):
        return "waiting_for_charger"
    # actively_charging = bot is physically on the charger and receiving power
    if getattr(bot, "actively_charging", False):
        return "charging"
    if brain and getattr(brain, "is_cat_frozen", False):
        return "cat_freeze"
    if brain and getattr(brain, "isAvoidingCat", False):
        return "avoid_cat"
    if brain and getattr(brain, "isAvoidingDebris", False):
        return "avoid_debris"
    if brain and getattr(brain, "isAvoiding", False):
        return "avoid_bot"
    # charger flag means "seeking charger" (low battery, navigating to charger)
    if getattr(bot, "charger", False):
        return "seeking_charger"
    if getattr(bot, "path", None):
        return "path_following"
    return "wander"


def derive_cat_mode(cat):
    if getattr(cat, "isJumping", False):
        return "panic_jump"
    if getattr(cat, "isAvoiding", False):
        return "avoid_bot"
    return "wander"
