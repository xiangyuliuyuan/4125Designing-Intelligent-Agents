import random

from ui import renderer


class Lamp:
    def __init__(self, namep):
        self.centreX = random.randint(100, 900)
        self.centreY = random.randint(100, 900)
        self.name = namep

    def draw(self, canvas):
        renderer.draw_lamp(canvas, self)

    def getLocation(self):
        return self.centreX, self.centreY
