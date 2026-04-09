
# class Counter:
#     def __init__(self):
#         self.dirtCollected = 0
#
#     def itemCollected(self,canvas,debris_count):
#         self.dirtCollected += 1
#         canvas.delete("dirtCount")
#         canvas.create_text(50,20,anchor="w",\
#                            text="Dirt collected: "+str(self.dirtCollected),\
#                            tags="dirtCount")
#         canvas.create_text(50, 35, anchor="w",\
#                            text="debris: " + str(debris_count),\
#                            tags="debrisCount")

class Counter():
    def __init__(self):
        self.dirtCollected = 0
        self.collected_label = None
        self.debris_label = None
        self.initial_debris = 0

    def set_collected_label(self, label):
        self.collected_label = label
        self.update_collected_display()

    def set_debris_label(self, label):
        self.debris_label = label

    def set_initial_debris(self, count):
        self.initial_debris = count
        self.update_debris_display(0)

    def update_collected_display(self):
        if self.collected_label:
            self.collected_label.set(str(self.dirtCollected))

    def update_debris_display(self, current_debris):
        if self.debris_label:
            self.debris_label.set(str(current_debris))

    def itemCollected(self, canvas, debris_count):
        self.dirtCollected += 1
        self.update_collected_display()
        # 可选：在canvas上显示临时消息
        # canvas.create_text(500, 50, text=f"+1", fill="green", font=("Arial", 12), tags="message")
        # canvas.after(1000, lambda: canvas.delete("message"))

    def update_stats(self, agents, runtime):
        # 计算平均电量
        total_battery = 0
        active = 0
        for agent in agents:
            if hasattr(agent, 'battery'):
                total_battery += agent.battery
                active += 1
        avg_battery = total_battery // active if active > 0 else 0
        return active, avg_battery