import random

#
# class Charger():
#     def __init__(self, namep):
#         self.centreX = random.randint(0, 1000)
#         self.centreY = random.randint(0, 1000)
#         self.name = namep
#
#     def draw(self, canvas):
#         body = canvas.create_oval(self.centreX - 10, self.centreY - 10, \
#                                   self.centreX + 10, self.centreY + 10, \
#                                   fill="red", tags=self.name)
#
#     def getLocation(self):
#         return self.centreX, self.centreY

class Charger():
    def __init__(self, namep):
        self.centreX = random.randint(100, 900)
        self.centreY = random.randint(100, 900)
        self.name = namep
        self.is_charging = False  # 是否正在充电
        self.charging_bot = None  # 正在充电的机器人

    def draw(self, canvas):
        body = canvas.create_rectangle(self.centreX - 20, self.centreY - 20, \
                                       self.centreX + 20, self.centreY + 20, \
                                       fill="gray", tags=self.name)
        # 如果有机器人在充电，显示红色边框
        if self.is_charging:
            canvas.create_rectangle(self.centreX - 20, self.centreY - 20, \
                                    self.centreX + 20, self.centreY + 20, \
                                    outline="red", width=3, tags=self.name)

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