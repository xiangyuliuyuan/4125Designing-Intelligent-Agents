import random
import math


class Cat():
    def __init__(self, namep):
        self.name = namep
        self.x = random.randint(100, 900)
        self.y = random.randint(100, 900)
        self.theta = random.uniform(0.0, 2.0 * math.pi)
        self.speed = 5.0  # 猫的移动速度
        self.avoid_distance = 100  # 躲避机器人的距离阈值

        # 漫游相关属性
        self.turningCount = 0
        self.movingCount = random.randrange(50, 100)
        self.currentlyTurning = False

        # 避让相关属性
        self.avoidCount = 0
        self.isAvoiding = False
        self.avoidDirection = 0
        self.total_turn_frames = 22  # 90度转向所需帧数

        # 跳走相关属性
        self.isJumping = False  # 是否正在跳走
        self.jump_frames = 0  # 跳走动画帧数

    def draw(self, canvas):
        # 根据是否在跳走来改变颜色或大小
        if self.isJumping:
            # 跳走时变大一点，颜色变浅
            size = 18
            color = "lightcoral"
        else:
            size = 15
            color = "orange"

        # 绘制猫的身体（圆形）
        canvas.create_oval(self.x - size, self.y - size,
                           self.x + size, self.y + size,
                           fill=color, tags=self.name)

        # 绘制耳朵
        ear_points = [(self.x - 12, self.y - size),
                      (self.x, self.y - size - 10),
                      (self.x + 12, self.y - size)]
        canvas.create_polygon(ear_points, fill=color, tags=self.name)

        # 绘制眼睛
        canvas.create_oval(self.x - 6, self.y - 4,
                           self.x - 2, self.y,
                           fill="white", tags=self.name)
        canvas.create_oval(self.x + 2, self.y - 4,
                           self.x + 6, self.y,
                           fill="white", tags=self.name)
        canvas.create_oval(self.x - 5, self.y - 3,
                           self.x - 3, self.y - 1,
                           fill="black", tags=self.name)
        canvas.create_oval(self.x + 3, self.y - 3,
                           self.x + 5, self.y - 1,
                           fill="black", tags=self.name)

        # 绘制鼻子
        canvas.create_oval(self.x - 2, self.y + 1,
                           self.x + 2, self.y + 3,
                           fill="pink", tags=self.name)

        # 绘制胡须
        canvas.create_line(self.x - 8, self.y + 2,
                           self.x - 15, self.y,
                           fill="black", width=1, tags=self.name)
        canvas.create_line(self.x - 8, self.y + 3,
                           self.x - 15, self.y + 3,
                           fill="black", width=1, tags=self.name)
        canvas.create_line(self.x + 8, self.y + 2,
                           self.x + 15, self.y,
                           fill="black", width=1, tags=self.name)
        canvas.create_line(self.x + 8, self.y + 3,
                           self.x + 15, self.y + 3,
                           fill="black", width=1, tags=self.name)

        # 绘制尾巴
        tail_points = [(self.x - 12, self.y + 8),
                       (self.x - 20, self.y + 12),
                       (self.x - 18, self.y + 8)]
        canvas.create_line(tail_points, fill=color, width=3, tags=self.name)

    def jump_away(self, agents):
        """猫跳离机器人"""
        # 找到最近的机器人
        nearest_bot = None
        min_distance = float('inf')

        for agent in agents:
            if agent.__class__.__name__ == 'Bot':
                dx = agent.x - self.x
                dy = agent.y - self.y
                distance = math.sqrt(dx * dx + dy * dy)
                if distance < min_distance:
                    min_distance = distance
                    nearest_bot = agent

        if nearest_bot:
            # 在机器人周围随机生成位置（距离50-100像素）
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(50, 100)

            new_x = nearest_bot.x + math.cos(angle) * distance
            new_y = nearest_bot.y + math.sin(angle) * distance

            # 边界检查
            new_x = max(15, min(985, new_x))
            new_y = max(15, min(985, new_y))

            # 设置新位置
            self.x = new_x
            self.y = new_y

            # 设置跳走动画
            self.isJumping = True
            self.jump_frames = 10  # 跳走动画持续10帧

            print(f"{self.name} 跳到了机器人旁边！")

    def update(self, canvas, agents, dt):
        # 先检查是否与机器人重合（距离<30）
        for agent in agents:
            if agent.__class__.__name__ == 'Bot':
                dx = agent.x - self.x
                dy = agent.y - self.y
                distance = math.sqrt(dx * dx + dy * dy)
                if distance < 30:  # 重合或非常接近
                    self.jump_away(agents)
                    break

        # 跳走动画效果
        if self.isJumping:
            self.jump_frames -= 1
            if self.jump_frames <= 0:
                self.isJumping = False
            # 跳走时不需要移动和避让，直接更新显示
            canvas.delete(self.name)
            self.draw(canvas)
            return

        # 寻找最近的机器人（用于避让）
        nearest_bot = None
        min_distance = float('inf')

        for agent in agents:
            if agent.__class__.__name__ == 'Bot':
                dx = agent.x - self.x
                dy = agent.y - self.y
                distance = math.sqrt(dx * dx + dy * dy)
                if distance < min_distance and distance < self.avoid_distance:
                    min_distance = distance
                    nearest_bot = agent

        # 如果找到机器人，执行避让（90度转向）
        if nearest_bot:
            if self.isAvoiding:
                # 正在转向中
                if self.avoidCount > 0:
                    if self.avoidDirection == 1:  # 左转
                        self.theta -= 0.1
                    else:  # 右转
                        self.theta += 0.1
                    self.avoidCount -= 1

                    if self.avoidCount <= 0:
                        self.isAvoiding = False
                        print(f"{self.name} 已完成90度转向")
                        self.movingCount = random.randrange(50, 100)
                        self.currentlyTurning = False
                else:
                    self.isAvoiding = False
                    self.movingCount = random.randrange(50, 100)
                    self.currentlyTurning = False
            else:
                # 开始避让 - 原地转向90度
                self.isAvoiding = True
                self.avoidCount = self.total_turn_frames

                if random.choice([True, False]):
                    self.avoidDirection = 1
                    print(f"{self.name} 检测到机器人！向左原地转向90度")
                else:
                    self.avoidDirection = -1
                    print(f"{self.name} 检测到机器人！向右原地转向90度")
        else:
            # 没有机器人时，使用漫游机制
            if self.isAvoiding:
                self.isAvoiding = False
                self.avoidCount = 0

            if self.currentlyTurning:
                self.theta -= 0.05
                self.turningCount -= 1
                if self.turningCount <= 0:
                    self.currentlyTurning = False
                    self.movingCount = random.randrange(50, 100)
            else:
                self.movingCount -= 1
                if self.movingCount <= 0:
                    self.currentlyTurning = True
                    self.turningCount = random.randrange(20, 40)

        # 移动猫
        self.x += math.cos(self.theta) * self.speed
        self.y += math.sin(self.theta) * self.speed

        # 边界处理（环形世界）
        if self.x > 1000:
            self.x = 0
        if self.x < 0:
            self.x = 1000
        if self.y > 1000:
            self.y = 0
        if self.y < 0:
            self.y = 1000

        # 更新显示
        canvas.delete(self.name)
        self.draw(canvas)

    def getLocation(self):
        return self.x, self.y