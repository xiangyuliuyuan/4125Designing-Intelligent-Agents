import random

from ui import renderer


class Dirt:
    """基础垃圾类"""

    def __init__(self, namep, x=None, y=None):
        if x is not None and y is not None:
            self.centreX = x
            self.centreY = y
        else:
            self.centreX = random.randint(0, 1000)
            self.centreY = random.randint(0, 1000)
        self.name = namep
        self.type = "dirt"
        self.clean_count = 1

    def draw(self, canvas):
        renderer.draw_dirt(canvas, self)

    def getLocation(self):
        return self.centreX, self.centreY

    def is_cleanable(self):
        return True

    def clean(self, current_time=0):
        self.clean_count -= 1
        return self.clean_count <= 0


class plusDirt(Dirt):
    """增强型垃圾类，支持多种垃圾类型、大小、重量、清洁冷却"""

    def __init__(self, namep, x=None, y=None, trash_type="dust", size=None, weight=None):
        super().__init__(namep, x, y)
        self.type = trash_type
        self.size = self.get_size_by_type(trash_type) if size is None else size
        self.weight = self.get_weight_by_type(trash_type) if weight is None else weight

        self.is_collected = False
        self.clean_cooldown = 10
        self.last_clean_time = -self.clean_cooldown

        if trash_type == "liquid":
            self.clean_count = random.randint(3, 5)
        elif trash_type == "debris":
            self.clean_count = float("inf")
        else:
            self.clean_count = 1

    # 每种垃圾类型的尺寸范围 (min, max)
    _SIZE_RANGES = {
        "dust": (1, 2),
        "crumb": (1, 2),
        "paper": (2, 4),
        "liquid": (2, 5),
        "hair": (1, 3),
        "debris": (10, 12),
    }

    # 每种垃圾类型的重量范围 (min, max)
    _WEIGHT_RANGES = {
        "dust": (0.1, 0.5),
        "crumb": (0.2, 1.0),
        "paper": (1.0, 5.0),
        "liquid": (5.0, 20.0),
        "hair": (0.1, 0.3),
        "debris": (10.0, 50.0),
    }

    @staticmethod
    def get_size_by_type(trash_type):
        size_range = plusDirt._SIZE_RANGES.get(trash_type)
        if size_range:
            return random.uniform(*size_range)
        return 1

    @staticmethod
    def get_weight_by_type(trash_type):
        weight_range = plusDirt._WEIGHT_RANGES.get(trash_type)
        if weight_range:
            return random.uniform(*weight_range)
        return 0.1

    def draw_with_size(self, canvas):
        renderer.draw_dirt(canvas, self)

    def get_message(self):
        return [self.name, self.centreX, self.centreY, self.type, self.size, self.weight, self.clean_count]

    def is_cleanable(self):
        return self.type != "debris"

    def clean(self, current_time=0):
        if self.type == "debris":
            return False
        if current_time - self.last_clean_time < self.clean_cooldown:
            return False

        self.last_clean_time = current_time
        self.clean_count -= 1

        if self.clean_count <= 0:
            return True
        return False
