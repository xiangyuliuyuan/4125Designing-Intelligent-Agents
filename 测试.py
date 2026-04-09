import tkinter as tk
import random
import math
import numpy as np
import dirt
from counting import Counter
from charger import Charger
from astar import AStar
from cat import Cat
import time
import threading

# 全局控制变量
simulation_running = True
simulation_speed = 1.0
reset_flag = False
simulation_objects = None  # 存储仿真对象，用于重置
after_id = None  # 存储after任务的ID，用于取消


class Brain():

    def __init__(self, botp):
        self.bot = botp
        self.turningCount = 0
        self.movingCount = random.randrange(50, 100)
        self.currentlyTurning = False

        self.avoidCount = 0  # 避让计数
        self.isAvoiding = False  # 是否正在避让机器人
        self.avoidDirection = 0  # 避让方向：1左转，-1右转
        self.debug_counter = 0  # 调试计数器
        self.total_turn_frames = 22  # 90度转向所需帧数

        # 持续转向相关
        self.turn_angle_sum = 0
        self.full_circle_frames = 88  # 360度所需帧数

        # 重叠处理相关
        self.isOverlapping = False  # 是否正在处理重叠
        self.overlapCount = 0  # 重叠后退计数
        self.overlap_direction = 0  # 后退方向
        self.overlap_threshold = 20000  # 重叠检测阈值（从50000降低到30000，更容易触发）
        self.overlap_back_frames = 25  # 后退帧数（从15增加到25，后退更远）
        self.overlap_back_speed = 6.0  # 后退速度（从5.0增加到6.0，后退更快）

        # 杂物避让相关
        self.isAvoidingDebris = False  # 是否正在避让杂物
        self.debris_avoid_direction = 1  # 杂物避让方向（固定顺时针）
        self.debris_avoid_counter = 0  # 杂物避让计数

    def thinkAndAct(self, lightL, lightR, chargerL, chargerR, x, y, sl, sr, battery, debrisL=0, debrisR=0):
        newX = None
        newY = None

        # 检查是否有其他机器人靠近
        light_sum = lightL + lightR

        # 杂物感应值
        debris_sum = debrisL + debrisR

        # 检测重叠（感应值极高，说明距离非常近）
        is_overlap = light_sum > 50000

        # 调试输出
        self.debug_counter += 1
        if self.debug_counter >= 30:
            if light_sum > 5000 or debris_sum > 5000:
                print(
                    f"{self.bot.name} 机器人感应: {light_sum:.0f}, 杂物感应: {debris_sum:.0f}, 避让机器人={self.isAvoiding}, 避让杂物={self.isAvoidingDebris}, 重叠={is_overlap}")
            self.debug_counter = 0

        # 默认速度
        speedLeft = 5.0
        speedRight = 5.0

        # 电池优先级最高（低电量时覆盖其他行为）
        if battery < 600:
            if self.isAvoiding:
                self.isAvoiding = False
                self.avoidCount = 0
            if self.isOverlapping:
                self.isOverlapping = False
            if self.isAvoidingDebris:
                self.isAvoidingDebris = False

            # 向充电站转向
            if chargerR > chargerL:
                speedLeft = 2.0
                speedRight = -2.0
            elif chargerR < chargerL:
                speedLeft = -2.0
                speedRight = 2.0
            if abs(chargerR - chargerL) < chargerL * 0.1:
                speedLeft = 5.0
                speedRight = 5.0

            # toroidal geometry
            if x > 1000:
                newX = 0
            if x < 0:
                newX = 1000
            if y > 1000:
                newY = 0
            if y < 0:
                newY = 1000

            return speedLeft, speedRight, newX, newY

        # 杂物避让（最高优先级，仅次于重叠）
        if debris_sum > 5000 or self.isAvoidingDebris:
            if not self.isAvoidingDebris:
                self.isAvoidingDebris = True
                self.debris_avoid_counter = 0
                print(f"{self.bot.name} 检测到杂物！开始顺时针持续转向避让")

            # 持续顺时针转向
            speedLeft = 3.0
            speedRight = -3.0
            self.debris_avoid_counter += 1

            # 检查是否已远离杂物
            if debris_sum <= 3000:
                print(f"{self.bot.name} 已远离杂物，结束避让")
                self.isAvoidingDebris = False
                self.debris_avoid_counter = 0
                speedLeft = 5.0
                speedRight = 5.0

            # toroidal geometry
            if x > 1000:
                newX = 0
            if x < 0:
                newX = 1000
            if y > 1000:
                newY = 0
            if y < 0:
                newY = 1000

            return speedLeft, speedRight, newX, newY

        # 重叠处理（优先级次之）
        if is_overlap or self.isOverlapping:
            if not self.isOverlapping:
                self.isOverlapping = True
                self.overlapCount = 15
                self.overlap_direction = random.choice([-1, 1])
                print(f"{self.bot.name} 检测到重叠！开始后退分开")

            if self.overlapCount > 0:
                speedLeft = -5.0 * self.overlap_direction
                speedRight = -5.0 * self.overlap_direction
                self.overlapCount -= 1
            else:
                self.isOverlapping = False
                print(f"{self.bot.name} 重叠处理完成")
                speedLeft = 5.0
                speedRight = 5.0

            # toroidal geometry
            if x > 1000:
                newX = 0
            if x < 0:
                newX = 1000
            if y > 1000:
                newY = 0
            if y < 0:
                newY = 1000

            return speedLeft, speedRight, newX, newY

        # 机器人避让逻辑：持续转向直到远离
        if self.isAvoiding:
            if light_sum <= 3000:
                print(f"{self.bot.name} 已远离机器人，结束避让")
                self.isAvoiding = False
                self.turn_angle_sum = 0
                self.movingCount = random.randrange(50, 100)
                self.currentlyTurning = False
                speedLeft = 5.0
                speedRight = 5.0
            else:
                if self.avoidDirection == 1:
                    speedLeft = 3.0
                    speedRight = -3.0
                else:
                    speedLeft = -3.0
                    speedRight = 3.0

                self.turn_angle_sum += 1

                if self.turn_angle_sum >= self.full_circle_frames:
                    print(f"{self.bot.name} 已转一圈仍未远离，切换转向方向")
                    self.avoidDirection = -self.avoidDirection
                    self.turn_angle_sum = 0

        # 检测到其他机器人靠近
        elif light_sum > 3000:
            self.isAvoiding = True
            self.turn_angle_sum = 0

            if random.choice([True, False]):
                self.avoidDirection = 1
                print(f"{self.bot.name} 检测到机器人！开始顺时针持续转向")
            else:
                self.avoidDirection = -1
                print(f"{self.bot.name} 检测到机器人！开始逆时针持续转向")

            if self.avoidDirection == 1:
                speedLeft = 3.0
                speedRight = -3.0
            else:
                speedLeft = -3.0
                speedRight = 3.0

        # 漫游行为
        else:
            if self.currentlyTurning == True:
                speedLeft = -2.0
                speedRight = 2.0
                self.turningCount -= 1
                if self.turningCount <= 0:
                    self.currentlyTurning = False
                    self.movingCount = random.randrange(50, 100)
            else:
                speedLeft = 5.0
                speedRight = 5.0
                self.movingCount -= 1
                if self.movingCount <= 0:
                    self.currentlyTurning = True
                    self.turningCount = random.randrange(20, 40)

        # toroidal geometry
        if x > 1000:
            newX = 0
        if x < 0:
            newX = 1000
        if y > 1000:
            newY = 0
        if y < 0:
            newY = 1000

        return speedLeft, speedRight, newX, newY


class Bot():

    def __init__(self, namep):
        self.name = namep
        self.x = random.randint(100, 900)
        self.y = random.randint(100, 900)
        self.theta = random.uniform(0.0, 2.0 * math.pi)
        self.ll = 60  # axle width
        self.sl = 0.0
        self.sr = 0.0
        self.battery = 1000
        self.path = []
        self.target_charger = None
        self.astar = None  # A* 算法实例
        self.battery_low_threshold = 600  # 低电量阈值
        self.low_battery_active = False  # 是否处于低电量静止状态
        self.path_calculated = False  # 是否已计算路径
        self.charger = False  # 充电模式
        self.sensorPositions = [0, 0, 0, 0]  # 初始化传感器位置
        self.wait_counter = 0  # 等待充电站时的计数器
        self.frame_counter = 0  # 帧计数器，用于垃圾清洁冷却

    def setAStar(self, astar):
        self.astar = astar

    def thinkAndAct(self, agents, passiveObjects):
        # 感应灯光
        lightL, lightR = self.senseLight(passiveObjects)

        # 感应其他机器人（用于避让）
        botLightL, botLightR = self.senseOtherBots(agents)

        # 感应杂物（debris）
        debrisL, debrisR = self.senseDebris(passiveObjects)

        # 合并感应数据
        totalLightL = lightL + botLightL * 2
        totalLightR = lightR + botLightR * 2

        chargerL, chargerR = self.senseChargers(passiveObjects)
        self.sl, self.sr, xx, yy = self.brain.thinkAndAct \
            (totalLightL, totalLightR, chargerL, chargerR, self.x, self.y, self.sl, self.sr, self.battery, debrisL,
             debrisR)
        if xx != None:
            self.x = xx
        if yy != None:
            self.y = yy

    def setBrain(self, brainp):
        self.brain = brainp

    def senseDebris(self, passiveObjects):
        """检测杂物（debris）的距离，用于避让"""
        debrisL = 0.0
        debrisR = 0.0

        for obj in passiveObjects:
            if hasattr(obj, 'type') and obj.type == 'debris':
                lx, ly = obj.getLocation()
                distanceL = math.sqrt((lx - self.sensorPositions[0]) * (lx - self.sensorPositions[0]) + \
                                      (ly - self.sensorPositions[1]) * (ly - self.sensorPositions[1]))
                distanceR = math.sqrt((lx - self.sensorPositions[2]) * (lx - self.sensorPositions[2]) + \
                                      (ly - self.sensorPositions[3]) * (ly - self.sensorPositions[3]))

                if distanceL < 150:
                    if distanceL > 0:
                        debrisL += 1000000 / (distanceL * distanceL)
                if distanceR < 150:
                    if distanceR > 0:
                        debrisR += 1000000 / (distanceR * distanceR)

        return debrisL, debrisR

    # returns the output from polling the light sensors
    def senseLight(self, passiveObjects):
        lightL = 0.0
        lightR = 0.0

        # 感应灯光
        for pp in passiveObjects:
            if isinstance(pp, Lamp):
                lx, ly = pp.getLocation()
                distanceL = math.sqrt((lx - self.sensorPositions[0]) * (lx - self.sensorPositions[0]) + \
                                      (ly - self.sensorPositions[1]) * (ly - self.sensorPositions[1]))
                distanceR = math.sqrt((lx - self.sensorPositions[2]) * (lx - self.sensorPositions[2]) + \
                                      (ly - self.sensorPositions[3]) * (ly - self.sensorPositions[3]))
                if distanceL > 0:
                    lightL += 200000 / (distanceL * distanceL)
                if distanceR > 0:
                    lightR += 200000 / (distanceR * distanceR)

        return lightL, lightR

    def senseOtherBots(self, agents):
        """检测其他机器人的距离，用于避让"""
        lightL = 0.0
        lightR = 0.0

        for agent in agents:
            if agent is not self and isinstance(agent, Bot):  # 排除自己
                # 获取其他机器人的位置
                bot_x, bot_y = agent.x, agent.y

                # 计算距离
                distanceL = math.sqrt((bot_x - self.sensorPositions[0]) * (bot_x - self.sensorPositions[0]) + \
                                      (bot_y - self.sensorPositions[1]) * (bot_y - self.sensorPositions[1]))
                distanceR = math.sqrt((bot_x - self.sensorPositions[2]) * (bot_x - self.sensorPositions[2]) + \
                                      (bot_y - self.sensorPositions[3]) * (bot_y - self.sensorPositions[3]))

                # 增加感应距离和强度，更容易触发避让
                if distanceL < 200:  # 增加感应距离到200
                    # 增加强度系数，让机器人更容易检测到
                    if distanceL > 0:
                        lightL += 8000000 / (distanceL * distanceL)
                if distanceR < 200:
                    if distanceR > 0:
                        lightR += 8000000 / (distanceR * distanceR)

        return lightL, lightR

    # returns sensors values that detect chargers
    def senseChargers(self, passiveObjects):
        chargerL = 0.0
        chargerR = 0.0
        for pp in passiveObjects:
            if isinstance(pp, Charger):
                lx, ly = pp.getLocation()
                distanceL = math.sqrt((lx - self.sensorPositions[0]) * (lx - self.sensorPositions[0]) + \
                                      (ly - self.sensorPositions[1]) * (ly - self.sensorPositions[1]))
                distanceR = math.sqrt((lx - self.sensorPositions[2]) * (lx - self.sensorPositions[2]) + \
                                      (ly - self.sensorPositions[3]) * (ly - self.sensorPositions[3]))
                if distanceL > 0:
                    chargerL += 200000 / (distanceL * distanceL)
                if distanceR > 0:
                    chargerR += 200000 / (distanceR * distanceR)
        return chargerL, chargerR

    # what happens at each timestep
    def update(self, canvas, passiveObjects, dt):

        # 1. 电量消耗先判断是否在等待充电站
        waiting_for_charger = False

        # 检查是否在等待充电站
        if self.charger and self.path and self.battery < 600:
            if self.target_charger and self.target_charger.is_charging and self.target_charger.charging_bot != self:
                waiting_for_charger = True

        # 电量消耗：等待充电站时每5帧消耗1点电
        if waiting_for_charger:
            self.wait_counter += 1
            if self.wait_counter >= 5:
                self.battery -= 1
                self.wait_counter = 0
        else:
            self.battery -= 1
            self.wait_counter = 0

        if self.battery <= 0:
            self.battery = 0

        # 2. 低电量处理：计算路径
        if self.battery < self.battery_low_threshold:
            # 进入低电量状态
            if not self.low_battery_active:
                self.low_battery_active = True
                self.charger = True  # 进入充电模式

                # 寻找最近充电站（不检查是否可用，因为可能被占用）
                nearest_charger = None
                min_dist = float('inf')
                for obj in passiveObjects:
                    if isinstance(obj, Charger):
                        d = self.distanceTo(obj)
                        if d < min_dist:
                            min_dist = d
                            nearest_charger = obj

                if nearest_charger and not self.path_calculated:
                    self.target_charger = nearest_charger
                    cx, cy = nearest_charger.getLocation()
                    # 使用A*计算路径
                    path = self.astar.find_path(self.x, self.y, cx, cy, passiveObjects)
                    if path:
                        self.path = path
                        self.path_calculated = True
                        self.charger = True
                        print(f"{self.name} 电量不足，已计算最短路径，共 {len(path)} 步")
                    else:
                        print(f"{self.name} 无法找到通往充电站的路径")
                        self.path = []
                        self.path_calculated = True
        else:
            # 电量大于等于600时，清除低电量状态和路径
            if self.battery >= 1000:
                self.low_battery_active = False
                self.path_calculated = False
                self.path = []
                self.target_charger = None
                self.charger = False

        # 3. 充电检测 - 修复逻辑
        for obj in passiveObjects:
            if isinstance(obj, Charger) and self.distanceTo(obj) < 80:
                if self.charger and self.battery < 1000:
                    # 检查充电站是否被其他机器人占用
                    if obj.is_charging and obj.charging_bot != self:
                        # 充电站被其他机器人占用，等待
                        self.sl = 0.0
                        self.sr = 0.0
                        print(f"{self.name} 充电站被占用，等待中...")
                    else:
                        # 充电站空闲或者是自己正在充电
                        if not obj.is_charging:
                            # 首次获取充电权限
                            if obj.start_charging(self):
                                print(f"{self.name} 开始充电")

                        # 充电
                        self.battery += 10
                        self.sl = 0.0
                        self.sr = 0.0

                        # 当电池充满时自动退出充电模式
                        if self.battery >= 1000:
                            obj.stop_charging()
                            self.charger = False
                            self.low_battery_active = False
                            self.path_calculated = False
                            self.path = []
                            print(f"{self.name} 已充满电，退出充电模式")

        # 4. 路径跟随（只在低电量且有路径时执行，且充电站未被占用）
        if self.charger and self.path and self.battery < 600:
            # 检查目标充电站是否被其他机器人占用
            if self.target_charger and self.target_charger.is_charging and self.target_charger.charging_bot != self:
                # 充电站被其他机器人占用，原地等待
                self.sl = 0.0
                self.sr = 0.0
                print(f"{self.name} 充电站被占用，等待中...")
                self.move(canvas, dt)
                return

            # # 获取下一个目标点
            # if self.path:
            #     target_x, target_y = self.path[0]
            #     dx = target_x - self.x
            #     dy = target_y - self.y
            #     distance = math.sqrt(dx * dx + dy * dy)
            #
            #     if distance < 20:  # 到达当前目标点
            #         self.path.pop(0)
            #         if not self.path:
            #             print(f"{self.name} 到达充电站附近")
            #     else:
            #         # 计算目标方向角
            #         target_angle = math.atan2(dy, dx)
            #         angle_diff = target_angle - self.theta
            #
            #         # 归一化角度差
            #         if angle_diff > math.pi:
            #             angle_diff -= 2 * math.pi
            #         elif angle_diff < -math.pi:
            #             angle_diff += 2 * math.pi
            #
            #         # 根据角度差设置速度（覆盖避让和漫游）
            #         if abs(angle_diff) < 0.1:
            #             self.sl = 3.0
            #             self.sr = 3.0
            #         elif angle_diff > 0:
            #             self.sl = -2.0
            #             self.sr = 2.0
            #         else:
            #             self.sl = 2.0
            #             self.sr = -2.0
            #
            #         # 覆盖 brain 设置的速度
            #         self.brain.isAvoiding = False  # 路径跟随时不避让

        # 移动机器人
        self.move(canvas, dt)

    # draws the robot at its current position
    def draw(self, canvas):
        points = [(self.x + 30 * math.sin(self.theta)) - 30 * math.sin((math.pi / 2.0) - self.theta), \
                  (self.y - 30 * math.cos(self.theta)) - 30 * math.cos((math.pi / 2.0) - self.theta), \
                  (self.x - 30 * math.sin(self.theta)) - 30 * math.sin((math.pi / 2.0) - self.theta), \
                  (self.y + 30 * math.cos(self.theta)) - 30 * math.cos((math.pi / 2.0) - self.theta), \
                  (self.x - 30 * math.sin(self.theta)) + 30 * math.sin((math.pi / 2.0) - self.theta), \
                  (self.y + 30 * math.cos(self.theta)) + 30 * math.cos((math.pi / 2.0) - self.theta), \
                  (self.x + 30 * math.sin(self.theta)) + 30 * math.sin((math.pi / 2.0) - self.theta), \
                  (self.y - 30 * math.cos(self.theta)) + 30 * math.cos((math.pi / 2.0) - self.theta) \
                  ]

        # 根据状态改变机器人颜色
        if hasattr(self, 'brain') and self.brain.isAvoiding:
            canvas.create_polygon(points, fill="orange", tags=self.name)  # 避让时橙色
        elif self.charger:
            canvas.create_polygon(points, fill="green", tags=self.name)  # 充电模式绿色
        else:
            canvas.create_polygon(points, fill="blue", tags=self.name)  # 正常蓝色

        self.sensorPositions = [(self.x + 20 * math.sin(self.theta)) + 30 * math.sin((math.pi / 2.0) - self.theta), \
                                (self.y - 20 * math.cos(self.theta)) + 30 * math.cos((math.pi / 2.0) - self.theta), \
                                (self.x - 20 * math.sin(self.theta)) + 30 * math.sin((math.pi / 2.0) - self.theta), \
                                (self.y + 20 * math.cos(self.theta)) + 30 * math.cos((math.pi / 2.0) - self.theta) \
                                ]

        centre1PosX = self.x
        centre1PosY = self.y
        canvas.create_oval(centre1PosX - 16, centre1PosY - 16, \
                           centre1PosX + 16, centre1PosY + 16, \
                           fill="gold", tags=self.name)
        canvas.create_text(self.x, self.y, text=str(self.battery), tags=self.name)

        wheel1PosX = self.x - 30 * math.sin(self.theta)
        wheel1PosY = self.y + 30 * math.cos(self.theta)
        canvas.create_oval(wheel1PosX - 3, wheel1PosY - 3, \
                           wheel1PosX + 3, wheel1PosY + 3, \
                           fill="red", tags=self.name)

        wheel2PosX = self.x + 30 * math.sin(self.theta)
        wheel2PosY = self.y - 30 * math.cos(self.theta)
        canvas.create_oval(wheel2PosX - 3, wheel2PosY - 3, \
                           wheel2PosX + 3, wheel2PosY + 3, \
                           fill="green", tags=self.name)

        sensor1PosX = self.sensorPositions[0]
        sensor1PosY = self.sensorPositions[1]
        sensor2PosX = self.sensorPositions[2]
        sensor2PosY = self.sensorPositions[3]
        canvas.create_oval(sensor1PosX - 3, sensor1PosY - 3, \
                           sensor1PosX + 3, sensor1PosY + 3, \
                           fill="yellow", tags=self.name)
        canvas.create_oval(sensor2PosX - 3, sensor2PosY - 3, \
                           sensor2PosX + 3, sensor2PosY + 3, \
                           fill="yellow", tags=self.name)

        # 绘制路径（如果有）
        if self.path and len(self.path) >= 2:
            points = []
            for (x, y) in self.path:
                points.extend([x, y])
            canvas.create_line(points, fill='gray', width=1, tags=self.name)

    # handles the physics of the movement
    def move(self, canvas, dt):
        if self.sl == self.sr:
            R = 0
        else:
            R = (self.ll / 2.0) * ((self.sr + self.sl) / (self.sl - self.sr))
        omega = (self.sl - self.sr) / self.ll
        ICCx = self.x - R * math.sin(self.theta)  # instantaneous centre of curvature
        ICCy = self.y + R * math.cos(self.theta)
        m = np.matrix([[math.cos(omega * dt), -math.sin(omega * dt), 0], \
                       [math.sin(omega * dt), math.cos(omega * dt), 0], \
                       [0, 0, 1]])
        v1 = np.matrix([[self.x - ICCx], [self.y - ICCy], [self.theta]])
        v2 = np.matrix([[ICCx], [ICCy], [omega * dt]])
        newv = np.add(np.dot(m, v1), v2)
        newX = newv.item(0)
        newY = newv.item(1)
        newTheta = newv.item(2)
        newTheta = newTheta % (2.0 * math.pi)  # make sure angle doesn't go outside [0.0,2*pi)
        self.x = newX
        self.y = newY
        self.theta = newTheta
        if self.sl == self.sr:  # straight line movement
            self.x += self.sr * math.cos(self.theta)  # sr wlog
            self.y += self.sr * math.sin(self.theta)
        canvas.delete(self.name)
        self.draw(canvas)

    # 计算距离
    def distanceTo(self, obj):
        xx, yy = obj.getLocation()
        return math.sqrt(math.pow(self.x - xx, 2) + math.pow(self.y - yy, 2))

    def collectDirt(self, canvas, passiveObjects, count,debris_count):
        toDelete = []
        self.frame_counter += 1  # 增加帧计数

        for idx, rr in enumerate(passiveObjects):
            # 如果是plusDirt类型
            if isinstance(rr, dirt.plusDirt):
                # 且距离小于30
                if self.distanceTo(rr) < 30:
                    # 检查是否可清洁
                    if rr.is_cleanable():
                        # 尝试清洁，传入当前帧计数
                        if rr.clean(self.frame_counter):
                            # 清洁完成，删除垃圾
                            canvas.delete(rr.name)
                            toDelete.append(idx)
                            count.itemCollected(canvas,debris_count)
                            print(f"{self.name} 清除了 {rr.type}，总分: {count.dirtCollected}")
                        elif rr.clean_count > 0 and rr.clean_count != float('inf'):
                            # 还需要继续清洁，刷新显示
                            canvas.delete(rr.name)
                            rr.draw_with_size(canvas)
                            print(f"{self.name} 清洁了 {rr.type}，还需要 {rr.clean_count} 次")
                    else:
                        # 杂物无法清洁，不处理
                        pass

        for ii in sorted(toDelete, reverse=True):
            del passiveObjects[ii]  # 删除垃圾信息内存
        return passiveObjects


class Lamp():
    def __init__(self, namep):
        self.centreX = random.randint(100, 900)
        self.centreY = random.randint(100, 900)
        self.name = namep

    def draw(self, canvas):
        body = canvas.create_oval(self.centreX - 10, self.centreY - 10, \
                                  self.centreX + 10, self.centreY + 10, \
                                  fill="yellow", tags=self.name)

    def getLocation(self):
        return self.centreX, self.centreY


def initialise(window):
    # creat a window to display the scene
    window.resizable(False, False)
    canvas = tk.Canvas(window, width=1000, height=1000)  # the size of window
    canvas.pack()
    return canvas


def buttonClicked(x, y, agents):
    for rr in agents:
        if isinstance(rr, Bot):
            rr.x = x
            rr.y = y


def createObjects(canvas, noOfBots=1, noOfLights=2, noOfCharger=1, amountOfDirt=300,
                  dirt_plus=False, noOfCats=1, count=None, debris_count_initial=0):
    """创建所有对象"""
    agents = []
    passiveObjects = []
    cats = []

    if count is None:
        count = Counter()

    debris_count = debris_count_initial

    width = canvas.winfo_width()
    height = canvas.winfo_height()
    if width <= 1:
        width = 1000
    if height <= 1:
        height = 1000
    astar = AStar(width, height, grid_size=20)

    # 生成猫
    for i in range(noOfCats):
        cat = Cat(f"Cat{i}")
        cats.append(cat)
        cat.draw(canvas)

    # 生成充电站
    chargers = []
    for i in range(noOfCharger):
        charger = Charger(f"Charger{i}")
        passiveObjects.append(charger)
        chargers.append(charger)
        charger.draw(canvas)

    # 生成机器人
    for i in range(noOfBots):
        bot = Bot(f"Bot{i}")
        bot.setAStar(astar)
        bot.target_charger_list = chargers
        brain = Brain(bot)
        bot.setBrain(brain)
        agents.append(bot)
        bot.draw(canvas)

    # 生成光源
    for i in range(noOfLights):
        lamp = Lamp(f"Lamp{i}")
        passiveObjects.append(lamp)
        lamp.draw(canvas)

    # 垃圾生成
    for i in range(amountOfDirt):
        if dirt_plus:
            x = random.randint(0, 1000)
            y = random.randint(0, 1000)
            trash_type = random.choice(["dust", "crumb", "paper", "liquid", "hair", "debris"])

            if trash_type == "debris":
                debris_count += 1

            dirt_obj = dirt.plusDirt(
                f"Dirt{i}", x, y, trash_type, size=1, weight=0.5
            )
            passiveObjects.append(dirt_obj)
            dirt_obj.draw_with_size(canvas)
        else:
            dirt_obj = dirt.Dirt(f"Dirt{i}")
            passiveObjects.append(dirt_obj)
            dirt_obj.draw(canvas)

    canvas.bind("<Button-1>", lambda event: buttonClicked(event.x, event.y, agents))
    return agents, passiveObjects, count, cats, debris_count, chargers, astar


def update_stats(canvas, agents, passiveObjects, count, cats, debris_count,
                 collected_label, debris_label, active_bots_label, avg_battery_label,
                 runtime_label, start_time, frame_count):
    """更新统计面板"""
    # 更新杂物数量
    current_debris = 0
    for obj in passiveObjects:
        if hasattr(obj, 'type') and obj.type == 'debris':
            current_debris += 1
    debris_label.config(text=f"杂物剩余: {current_debris}")

    # 更新机器人统计
    active_bots = 0
    total_battery = 0
    for agent in agents:
        if hasattr(agent, 'battery'):
            active_bots += 1
            total_battery += agent.battery
    active_bots_label.config(text=f"活跃机器人: {active_bots}")
    avg_battery = total_battery // active_bots if active_bots > 0 else 0
    avg_battery_label.config(text=f"平均电量: {avg_battery}")

    # 更新运行时间
    elapsed_time = time.time() - start_time
    runtime_label.config(text=f"运行时间: {elapsed_time:.1f}s")

    # 更新已收集垃圾
    collected_label.config(text=f"已收集垃圾: {count.dirtCollected}")


def moveIt(canvas, agents, passiveObjects, count, cats, debris_count,
           stats_vars, start_time, speed_var, pause_button, chargers, astar):
    """主仿真循环"""
    global simulation_running, simulation_speed, reset_flag, after_id

    if reset_flag:
        reset_flag = False
        return

    if not simulation_running:
        after_id = canvas.after(50, moveIt, canvas, agents, passiveObjects, count, cats, debris_count,
                                stats_vars, start_time, speed_var, pause_button, chargers, astar)
        return

    simulation_speed = speed_var.get()

    try:
        # 运行仿真
        for rr in agents:
            rr.thinkAndAct(agents, passiveObjects)
            rr.update(canvas, passiveObjects, 1.0 * simulation_speed)
            passiveObjects = rr.collectDirt(canvas, passiveObjects, count, debris_count)

        # 更新猫
        for cat in cats:
            cat.update(canvas, agents, 1.0 * simulation_speed)

        # 更新统计面板
        current_debris = sum(1 for obj in passiveObjects if hasattr(obj, 'type') and obj.type == 'debris')
        stats_vars["debris"].config(text=f"杂物剩余: {current_debris}")

        active_bots = len(agents)
        total_battery = sum(agent.battery for agent in agents if hasattr(agent, 'battery'))
        avg_battery = total_battery // active_bots if active_bots > 0 else 0
        stats_vars["active_bots"].config(text=f"活跃机器人: {active_bots}")
        stats_vars["avg_battery"].config(text=f"平均电量: {avg_battery}")
        stats_vars["cats_count"].config(text=f"猫数量: {len(cats)}")
        stats_vars["chargers_count"].config(text=f"充电站: {len(chargers)}")

        elapsed_time = time.time() - start_time
        stats_vars["runtime"].config(text=f"运行时间: {elapsed_time:.1f}s")
        stats_vars["collected"].config(text=f"已收集垃圾: {count.dirtCollected}")

    except Exception as e:
        print(f"仿真出错: {e}")
        return

    after_id = canvas.after(int(50 / simulation_speed), moveIt, canvas, agents, passiveObjects,
                            count, cats, current_debris, stats_vars, start_time,
                            speed_var, pause_button, chargers, astar)

def initialise(parent):
    canvas = tk.Canvas(parent, width=1000, height=1000, bg="white")
    canvas.pack()
    return canvas


def buttonClicked(x, y, agents):
    for rr in agents:
        if isinstance(rr, Bot):
            rr.x = x
            rr.y = y


def reset_simulation(canvas, main_frame, stats_vars, speed_var, pause_button):
    """完全重置仿真"""
    global simulation_running, reset_flag, after_id

    # 设置重置标志，停止当前循环
    reset_flag = True
    simulation_running = False

    # 取消当前的after任务
    if after_id is not None:
        canvas.after_cancel(after_id)
        after_id = None

    # 清空canvas
    canvas.delete("all")

    # 重新创建所有对象
    count = Counter()
    agents, passiveObjects, count, cats, debris_count, chargers, astar = createObjects(
        canvas, noOfBots=3, noOfLights=2, noOfCharger=2,
        dirt_plus=True, noOfCats=4, count=count, debris_count_initial=0
    )

    # 重置统计显示
    stats_vars["collected"].config(text="已收集垃圾: 0")
    stats_vars["debris"].config(text=f"杂物剩余: {debris_count}")
    stats_vars["active_bots"].config(text="活跃机器人: 3")
    stats_vars["avg_battery"].config(text="平均电量: 1000")
    stats_vars["runtime"].config(text="运行时间: 0.0s")
    stats_vars["cats_count"].config(text=f"猫数量: {len(cats)}")
    stats_vars["chargers_count"].config(text=f"充电站: {len(chargers)}")

    # 重置开始时间
    start_time = time.time()

    # 重置标志
    reset_flag = False
    simulation_running = True

    # 返回所有对象
    return agents, passiveObjects, count, cats, debris_count, chargers, astar, start_time


def toggle_pause(pause_button):
    """切换暂停状态"""
    global simulation_running
    simulation_running = not simulation_running
    if simulation_running:
        pause_button.config(text="⏸ 暂停", bg="orange")
    else:
        pause_button.config(text="▶ 继续", bg="green")


def add_random_dirt(canvas, passiveObjects):
    """添加随机垃圾"""
    x = random.randint(0, 1000)
    y = random.randint(0, 1000)
    trash_type = random.choice(["dust", "crumb", "paper", "liquid", "hair", "debris"])
    dirt_obj = dirt.plusDirt(
        "Dirt_" + str(random.randint(10000, 99999)),
        x, y, trash_type, size=1, weight=0.5
    )
    passiveObjects.append(dirt_obj)
    dirt_obj.draw_with_size(canvas)
    print(f"添加了新的{trash_type}垃圾在({x},{y})")
    return passiveObjects





def add_bot(canvas, agents, passiveObjects, astar, chargers):
    """添加一个新机器人"""
    bot_num = len(agents)
    bot = Bot(f"Bot{bot_num}")
    bot.setAStar(astar)
    bot.target_charger_list = chargers
    brain = Brain(bot)
    bot.setBrain(brain)
    agents.append(bot)
    bot.draw(canvas)
    print(f"添加了机器人 {bot.name}")
    return agents


def remove_bot(canvas, agents):
    """删除最后一个机器人（至少保留1个）"""
    if len(agents) > 1:
        removed = agents.pop()
        canvas.delete(removed.name)
        print(f"删除了机器人 {removed.name}")
    else:
        print("至少需要保留1个机器人")
    return agents


def add_cat(canvas, cats):
    """添加一个新猫"""
    cat_num = len(cats)
    cat = Cat(f"Cat{cat_num}")
    cats.append(cat)
    cat.draw(canvas)
    print(f"添加了猫 {cat.name}")
    return cats


def remove_cat(canvas, cats):
    """删除最后一个猫"""
    if len(cats) > 0:
        removed = cats.pop()
        canvas.delete(removed.name)
        print(f"删除了猫 {removed.name}")
    else:
        print("没有猫可以删除")
    return cats


def add_charger(canvas, passiveObjects, chargers):
    """添加一个新充电站"""
    charger_num = len(chargers)
    charger = Charger(f"Charger{charger_num}")
    passiveObjects.append(charger)
    chargers.append(charger)
    charger.draw(canvas)
    print(f"添加了充电站 {charger.name}")
    return passiveObjects, chargers


def remove_charger(canvas, passiveObjects, chargers):
    """删除最后一个充电站"""
    if len(chargers) > 1:
        removed = chargers.pop()
        # 从passiveObjects中移除
        for i, obj in enumerate(passiveObjects):
            if obj is removed:
                passiveObjects.pop(i)
                break
        canvas.delete(removed.name)
        print(f"删除了充电站 {removed.name}")
    else:
        print("至少需要保留1个充电站")
    return passiveObjects, chargers


def add_random_dirt_with_count(canvas, passiveObjects, debris_label, stats_vars):
    """添加随机垃圾并更新显示"""
    x = random.randint(0, 1000)
    y = random.randint(0, 1000)
    trash_type = random.choice(["dust", "crumb", "paper", "liquid", "hair", "debris"])
    dirt_obj = dirt.plusDirt(
        "Dirt_" + str(random.randint(10000, 99999)),
        x, y, trash_type, size=1, weight=0.5
    )
    passiveObjects.append(dirt_obj)
    dirt_obj.draw_with_size(canvas)

    # 更新杂物显示
    current_debris = sum(1 for obj in passiveObjects if hasattr(obj, 'type') and obj.type == 'debris')
    stats_vars["debris"].config(text=f"杂物剩余: {current_debris}")

    print(f"添加了新的{trash_type}垃圾在({x},{y})")
    return passiveObjects


def remove_dirt(canvas, passiveObjects, stats_vars):
    """删除最后一个垃圾"""
    # 从后往前找最后一个垃圾
    for i in range(len(passiveObjects) - 1, -1, -1):
        obj = passiveObjects[i]
        if isinstance(obj, dirt.plusDirt) or isinstance(obj, dirt.Dirt):
            removed = passiveObjects.pop(i)
            canvas.delete(removed.name)
            print(f"删除了垃圾 {removed.name}")
            break

    # 更新杂物显示
    current_debris = sum(1 for obj in passiveObjects if hasattr(obj, 'type') and obj.type == 'debris')
    stats_vars["debris"].config(text=f"杂物剩余: {current_debris}")

    return passiveObjects


def main():
    window = tk.Tk()
    window.title("多智能体机器人仿真系统")

    # 创建主框架
    main_frame = tk.Frame(window)
    main_frame.pack()

    # 创建统计面板
    stats_frame = tk.Frame(main_frame, bg="lightgray", relief=tk.RAISED, bd=2)
    stats_frame.pack(fill=tk.X, padx=5, pady=5)

    # 创建控制面板
    control_frame = tk.Frame(main_frame, bg="#f0f0f0", relief=tk.RAISED, bd=2)
    control_frame.pack(fill=tk.X, padx=5, pady=5)

    # 创建canvas
    canvas = initialise(main_frame)

    # 创建统计变量
    stats_vars = {
        "collected": tk.Label(stats_frame, text="已收集垃圾: 0", font=("Arial", 10), bg="lightgray"),
        "debris": tk.Label(stats_frame, text="杂物剩余: 0", font=("Arial", 10), bg="lightgray"),
        "active_bots": tk.Label(stats_frame, text="活跃机器人: 0", font=("Arial", 10), bg="lightgray"),
        "avg_battery": tk.Label(stats_frame, text="平均电量: 0", font=("Arial", 10), bg="lightgray"),
        "runtime": tk.Label(stats_frame, text="运行时间: 0s", font=("Arial", 10), bg="lightgray"),
        "cats_count": tk.Label(stats_frame, text="猫数量: 0", font=("Arial", 10), bg="lightgray"),
        "chargers_count": tk.Label(stats_frame, text="充电站: 0", font=("Arial", 10), bg="lightgray")
    }

    # 统计面板标题
    title_label = tk.Label(stats_frame, text="📊 仿真统计面板", font=("Arial", 12, "bold"), bg="lightgray")
    title_label.pack(side=tk.TOP, pady=2)

    # 第一行统计
    row1 = tk.Frame(stats_frame, bg="lightgray")
    row1.pack(fill=tk.X)
    stats_vars["collected"].pack(side=tk.LEFT, padx=10)
    stats_vars["debris"].pack(side=tk.LEFT, padx=10)
    stats_vars["active_bots"].pack(side=tk.LEFT, padx=10)

    # 第二行统计
    row2 = tk.Frame(stats_frame, bg="lightgray")
    row2.pack(fill=tk.X, pady=2)
    stats_vars["avg_battery"].pack(side=tk.LEFT, padx=10)
    stats_vars["runtime"].pack(side=tk.LEFT, padx=10)
    stats_vars["cats_count"].pack(side=tk.LEFT, padx=10)
    stats_vars["chargers_count"].pack(side=tk.LEFT, padx=10)

    # 控制面板 - 速度控制
    speed_frame = tk.Frame(control_frame, bg="#f0f0f0")
    speed_frame.pack(side=tk.LEFT, padx=10)

    tk.Label(speed_frame, text="仿真速度:", bg="#f0f0f0", font=("Arial", 10)).pack(side=tk.LEFT)
    speed_var = tk.DoubleVar(value=1.0)
    speed_scale = tk.Scale(speed_frame, from_=0.5, to=3.0, resolution=0.1,
                           orient=tk.HORIZONTAL, length=150, variable=speed_var,
                           bg="#f0f0f0")
    speed_scale.pack(side=tk.LEFT, padx=5)
    speed_label = tk.Label(speed_frame, text="1.0x", bg="#f0f0f0", font=("Arial", 10))
    speed_label.pack(side=tk.LEFT)

    def update_speed_label(*args):
        speed_label.config(text=f"{speed_var.get():.1f}x")

    speed_var.trace("w", update_speed_label)

    # 控制按钮区域
    button_frame = tk.Frame(control_frame, bg="#f0f0f0")
    button_frame.pack(side=tk.LEFT, padx=20)

    # 机器人控制
    bot_frame = tk.LabelFrame(button_frame, text="机器人", bg="#f0f0f0", font=("Arial", 9))
    bot_frame.pack(side=tk.LEFT, padx=5)

    # 创建初始对象
    count = Counter()
    agents, passiveObjects, count, cats, debris_count, chargers, astar = createObjects(
        canvas, noOfBots=3, noOfLights=2, noOfCharger=2,
        dirt_plus=True, noOfCats=4, count=count, debris_count_initial=0
    )

    # 使用可变对象存储引用
    simulation_data = {
        "agents": agents,
        "passiveObjects": passiveObjects,
        "count": count,
        "cats": cats,
        "debris_count": debris_count,
        "chargers": chargers,
        "astar": astar,
        "start_time": time.time()
    }

    def add_bot_callback():
        simulation_data["agents"] = add_bot(canvas, simulation_data["agents"],
                                            simulation_data["passiveObjects"],
                                            simulation_data["astar"],
                                            simulation_data["chargers"])
        stats_vars["active_bots"].config(text=f"活跃机器人: {len(simulation_data['agents'])}")

    def remove_bot_callback():
        simulation_data["agents"] = remove_bot(canvas, simulation_data["agents"])
        stats_vars["active_bots"].config(text=f"活跃机器人: {len(simulation_data['agents'])}")

    tk.Button(bot_frame, text="➕ 机器人", bg="lightblue", font=("Arial", 9),
              command=add_bot_callback).pack(side=tk.LEFT, padx=2)
    tk.Button(bot_frame, text="➖ 机器人", bg="lightblue", font=("Arial", 9),
              command=remove_bot_callback).pack(side=tk.LEFT, padx=2)

    # 猫控制
    cat_frame = tk.LabelFrame(button_frame, text="猫", bg="#f0f0f0", font=("Arial", 9))
    cat_frame.pack(side=tk.LEFT, padx=5)

    def add_cat_callback():
        simulation_data["cats"] = add_cat(canvas, simulation_data["cats"])
        stats_vars["cats_count"].config(text=f"猫数量: {len(simulation_data['cats'])}")

    def remove_cat_callback():
        simulation_data["cats"] = remove_cat(canvas, simulation_data["cats"])
        stats_vars["cats_count"].config(text=f"猫数量: {len(simulation_data['cats'])}")

    tk.Button(cat_frame, text="➕ 猫", bg="orange", font=("Arial", 9),
              command=add_cat_callback).pack(side=tk.LEFT, padx=2)
    tk.Button(cat_frame, text="➖ 猫", bg="orange", font=("Arial", 9),
              command=remove_cat_callback).pack(side=tk.LEFT, padx=2)

    # 充电站控制
    charger_frame = tk.LabelFrame(button_frame, text="充电站", bg="#f0f0f0", font=("Arial", 9))
    charger_frame.pack(side=tk.LEFT, padx=5)

    def add_charger_callback():
        simulation_data["passiveObjects"], simulation_data["chargers"] = add_charger(
            canvas, simulation_data["passiveObjects"], simulation_data["chargers"])
        stats_vars["chargers_count"].config(text=f"充电站: {len(simulation_data['chargers'])}")

    def remove_charger_callback():
        simulation_data["passiveObjects"], simulation_data["chargers"] = remove_charger(
            canvas, simulation_data["passiveObjects"], simulation_data["chargers"])
        stats_vars["chargers_count"].config(text=f"充电站: {len(simulation_data['chargers'])}")

    tk.Button(charger_frame, text="➕ 充电站", bg="gray", font=("Arial", 9),
              command=add_charger_callback).pack(side=tk.LEFT, padx=2)
    tk.Button(charger_frame, text="➖ 充电站", bg="gray", font=("Arial", 9),
              command=remove_charger_callback).pack(side=tk.LEFT, padx=2)

    # 垃圾控制
    dirt_frame = tk.LabelFrame(button_frame, text="垃圾", bg="#f0f0f0", font=("Arial", 9))
    dirt_frame.pack(side=tk.LEFT, padx=5)

    def add_dirt_callback():
        simulation_data["passiveObjects"] = add_random_dirt_with_count(
            canvas, simulation_data["passiveObjects"], stats_vars["debris"], stats_vars)

    def remove_dirt_callback():
        simulation_data["passiveObjects"] = remove_dirt(
            canvas, simulation_data["passiveObjects"], stats_vars)

    tk.Button(dirt_frame, text="➕ 垃圾", bg="lightgreen", font=("Arial", 9),
              command=add_dirt_callback).pack(side=tk.LEFT, padx=2)
    tk.Button(dirt_frame, text="➖ 垃圾", bg="lightgreen", font=("Arial", 9),
              command=remove_dirt_callback).pack(side=tk.LEFT, padx=2)

    # 基本控制按钮
    basic_frame = tk.Frame(button_frame, bg="#f0f0f0")
    basic_frame.pack(side=tk.LEFT, padx=5)

    pause_button = tk.Button(basic_frame, text="⏸ 暂停", bg="orange", font=("Arial", 9),
                             command=lambda: toggle_pause(pause_button))
    pause_button.pack(side=tk.LEFT, padx=2)

    def reset_callback():
        global after_id
        result = reset_simulation(canvas, main_frame, stats_vars, speed_var, pause_button)
        if result:
            # 更新simulation_data中的所有数据
            simulation_data["agents"], simulation_data["passiveObjects"], simulation_data["count"], \
                simulation_data["cats"], simulation_data["debris_count"], simulation_data["chargers"], \
                simulation_data["astar"], simulation_data["start_time"] = result

            # 重新启动moveIt
            if after_id is not None:
                canvas.after_cancel(after_id)
            after_id = canvas.after(50, moveIt, canvas,
                                    simulation_data["agents"],
                                    simulation_data["passiveObjects"],
                                    simulation_data["count"],
                                    simulation_data["cats"],
                                    simulation_data["debris_count"],
                                    stats_vars,
                                    simulation_data["start_time"],
                                    speed_var,
                                    pause_button,
                                    simulation_data["chargers"],
                                    simulation_data["astar"])

    reset_button = tk.Button(basic_frame, text="🔄 重置", bg="lightblue", font=("Arial", 9),
                             command=reset_callback)
    reset_button.pack(side=tk.LEFT, padx=2)

    # 设置初始统计显示
    stats_vars["collected"].config(text="已收集垃圾: 0")
    stats_vars["debris"].config(text=f"杂物剩余: {debris_count}")
    stats_vars["active_bots"].config(text=f"活跃机器人: {len(agents)}")
    stats_vars["avg_battery"].config(text="平均电量: 1000")
    stats_vars["runtime"].config(text="运行时间: 0.0s")
    stats_vars["cats_count"].config(text=f"猫数量: {len(cats)}")
    stats_vars["chargers_count"].config(text=f"充电站: {len(chargers)}")

    # 键盘控制
    def key_handler(event):
        if event.keysym == 'space':
            toggle_pause(pause_button)
        elif event.keysym == 'r' or event.keysym == 'R':
            reset_callback()
        elif event.keysym == 'plus' or event.keysym == 'equal':
            speed_var.set(min(3.0, speed_var.get() + 0.1))
        elif event.keysym == 'minus':
            speed_var.set(max(0.5, speed_var.get() - 0.1))

    window.bind('<Key>', key_handler)

    # 启动主循环
    after_id = canvas.after(50, moveIt, canvas, agents, passiveObjects, count, cats, debris_count,
                            stats_vars, simulation_data["start_time"], speed_var, pause_button, chargers, astar)

    window.mainloop()


main()