import random

from ui import renderer


class Charger:
    """充电站实体，支持排他充电"""

    def __init__(self, namep):
        self.centreX = random.randint(100, 900)
        self.centreY = random.randint(100, 900)
        self.name = namep
        self.is_charging = False
        self.charging_bot = None

    def draw(self, canvas):
        renderer.draw_charger(canvas, self)

    def getLocation(self):
        return self.centreX, self.centreY

    def start_charging(self, bot):
        if not self.is_charging:
            self.is_charging = True
            self.charging_bot = bot
            return True
        return False

    def stop_charging(self):
        self.is_charging = False
        self.charging_bot = None
