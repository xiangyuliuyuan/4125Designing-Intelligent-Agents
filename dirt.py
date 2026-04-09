# import random
#
#
# class Dirt:
#     # 初始化垃圾
#     def __init__(self, namep, x=None, y=None):
#         # 如果给定垃圾坐标则使用垃圾坐标
#         if x is not None and y is not None:
#             self.centreX = x
#             self.centreY = y
#         # 否则在100-900间随机生成
#         else:
#             self.centreX = random.randint(0, 1000)
#             self.centreY = random.randint(0, 1000)
#         self.name = namep
#         self.clean_count = 1  # 需要清洁的次数，默认为1次
#
#     def draw(self, canvas):
#         body = canvas.create_oval(self.centreX - 1, self.centreY - 1, \
#                                   self.centreX + 1, self.centreY + 1, \
#                                   fill="grey", tags=self.name)
#
#     def getLocation(self):
#         return self.centreX, self.centreY
#
#     def is_cleanable(self):
#         return True
#
#     def clean(self):
#         self.clean_count -= 1
#         return self.clean_count <= 0
#
#
# class plusDirt(Dirt):
#     def __init__(self, namep, x=None, y=None, trash_type="dust", size=1, weight=0.5):
#         super().__init__(namep, x, y)
#         self.type = trash_type
#         # 如果没有指定size，则根据类型自动生成
#         if size == 1 and trash_type != "dust":
#             self.size = self.get_size_by_type(trash_type)
#         else:
#             self.size = size
#         # 如果没有指定weight,则根据类型自动生成
#         if weight == 0.5 and trash_type != "crumb":
#             self.weight = self.get_weight_by_type(trash_type)
#         else:
#             self.weight = weight
#
#         self.is_collected = False
#
#         # 根据垃圾类型设置清洁次数
#         if trash_type == "liquid":
#             self.clean_count = random.randint(3, 5)  # 液体需要3-5次清洁
#         elif trash_type == "debris":
#             self.clean_count = float('inf')  # 杂物无法清洁
#         else:
#             self.clean_count = 1  # 其他垃圾1次清洁
#
#     @staticmethod
#     def get_size_by_type(trash_type):
#         """根据垃圾类型返回大小（静态方法）"""
#         sizes = {
#             "dust": random.uniform(1, 2),
#             "crumb": random.uniform(1, 2),
#             "paper": random.uniform(2, 4),
#             "liquid": random.uniform(2, 5),
#             "hair": random.uniform(1, 3),
#             "debris": random.uniform(10, 12)
#         }
#         return sizes.get(trash_type, 1)
#
#     @staticmethod
#     def get_weight_by_type(trash_type):
#         weights = {
#             "dust": random.uniform(0.1, 0.5),  # 灰尘很轻
#             "crumb": random.uniform(0.2, 1.0),  # 碎屑较轻
#             "paper": random.uniform(1.0, 5.0),  # 纸屑中等
#             "liquid": random.uniform(5.0, 20.0),  # 液体较重
#             "hair": random.uniform(0.1, 0.3),  # 毛发很轻
#             "debris": random.uniform(10.0, 50.0)  # 杂物很重
#         }
#         return weights.get(trash_type, 0.1)
#
#     def _get_size_by_type(self):
#         """实例方法，根据自身类型返回大小"""
#         return self.get_size_by_type(self.type)
#
#     def draw_with_size(self, canvas):
#         """根据垃圾大小绘制不同尺寸的垃圾"""
#         # 根据大小调整绘制半径
#         radius = max(1, min(15, int(self.size)))
#
#         # 根据类型设置颜色
#         color = self._get_color_by_type()
#
#         # 如果是液体，显示剩余清洁次数
#         body = canvas.create_oval(
#             self.centreX - radius, self.centreY - radius,
#             self.centreX + radius, self.centreY + radius,
#             fill=color, tags=self.name
#         )
#
#         # 显示需要清洁的次数（仅对液体）
#         if self.type == "liquid" and self.clean_count != float('inf'):
#             canvas.create_text(self.centreX, self.centreY,
#                                text=str(self.clean_count),
#                                fill="white", font=("Arial", 8),
#                                tags=self.name)
#
#         # 杂物显示特殊标记
#         if self.type == "debris":
#             canvas.create_text(self.centreX, self.centreY,
#                                text="X", fill="red", font=("Arial", 10, "bold"),
#                                tags=self.name)
#
#         return body
#
#     def _get_color_by_type(self):
#         """根据垃圾类型返回不同的颜色"""
#         colors = {
#             "dust": "lightgray",
#             "crumb": "brown",
#             "paper": "white",
#             "liquid": "lightblue",
#             "hair": "darkgray",
#             "debris": "gray"
#         }
#         return colors.get(self.type, "gray")
#
#     def get_message(self):
#         message = [self.name, self.centreX, self.centreY, self.type, self.size, self.weight, self.clean_count]
#         return message
#
#     def is_cleanable(self):
#         """检查垃圾是否可清洁"""
#         return self.type != "debris"
#
#     def clean(self):
#         """清洁垃圾，返回是否完全清除"""
#         if self.type == "debris":
#             return False  # 杂物无法清洁
#
#         self.clean_count -= 1
#         if self.clean_count <= 0:
#             return True  # 清洁完成
#         return False  # 还需要继续清洁

import random


class Dirt:
    # 初始化垃圾
    def __init__(self, namep, x=None, y=None):
        # 如果给定垃圾坐标则使用垃圾坐标
        if x is not None and y is not None:
            self.centreX = x
            self.centreY = y
        # 否则在100-900间随机生成
        else:
            self.centreX = random.randint(0, 1000)
            self.centreY = random.randint(0, 1000)
        self.name = namep
        self.clean_count = 1  # 需要清洁的次数，默认为1次

    def draw(self, canvas):
        body = canvas.create_oval(self.centreX - 1, self.centreY - 1, \
                                  self.centreX + 1, self.centreY + 1, \
                                  fill="grey", tags=self.name)

    def getLocation(self):
        return self.centreX, self.centreY

    def is_cleanable(self):
        return True

    def clean(self, current_time=0):
        self.clean_count -= 1
        return self.clean_count <= 0


class plusDirt(Dirt):
    def __init__(self, namep, x=None, y=None, trash_type="dust", size=1, weight=0.5):
        super().__init__(namep, x, y)
        self.type = trash_type
        # 如果没有指定size，则根据类型自动生成
        if size == 1 and trash_type != "dust":
            self.size = self.get_size_by_type(trash_type)
        else:
            self.size = size
        # 如果没有指定weight,则根据类型自动生成
        if weight == 0.5 and trash_type != "crumb":
            self.weight = self.get_weight_by_type(trash_type)
        else:
            self.weight = weight

        self.is_collected = False
        self.last_clean_time = 0  # 上次清洁的时间戳
        self.clean_cooldown = 10  # 清洁冷却时间（帧数）

        # 根据垃圾类型设置清洁次数
        if trash_type == "liquid":
            self.clean_count = random.randint(3, 5)  # 液体需要3-5次清洁
        elif trash_type == "debris":
            self.clean_count = float('inf')  # 杂物无法清洁
        else:
            self.clean_count = 1  # 其他垃圾1次清洁

    @staticmethod
    def get_size_by_type(trash_type):
        """根据垃圾类型返回大小（静态方法）"""
        sizes = {
            "dust": random.uniform(1, 2),
            "crumb": random.uniform(1, 2),
            "paper": random.uniform(2, 4),
            "liquid": random.uniform(2, 5),
            "hair": random.uniform(1, 3),
            "debris": random.uniform(10, 12)
        }
        return sizes.get(trash_type, 1)

    @staticmethod
    def get_weight_by_type(trash_type):
        weights = {
            "dust": random.uniform(0.1, 0.5),  # 灰尘很轻
            "crumb": random.uniform(0.2, 1.0),  # 碎屑较轻
            "paper": random.uniform(1.0, 5.0),  # 纸屑中等
            "liquid": random.uniform(5.0, 20.0),  # 液体较重
            "hair": random.uniform(0.1, 0.3),  # 毛发很轻
            "debris": random.uniform(10.0, 50.0)  # 杂物很重
        }
        return weights.get(trash_type, 0.1)

    def _get_size_by_type(self):
        """实例方法，根据自身类型返回大小"""
        return self.get_size_by_type(self.type)

    def draw_with_size(self, canvas):
        """根据垃圾大小绘制不同尺寸的垃圾"""
        # 根据大小调整绘制半径
        radius = max(1, min(15, int(self.size)))

        # 根据类型设置颜色
        color = self._get_color_by_type()

        # 绘制垃圾本体
        body = canvas.create_oval(
            self.centreX - radius, self.centreY - radius,
            self.centreX + radius, self.centreY + radius,
            fill=color, tags=self.name
        )

        # 显示需要清洁的次数（仅对液体）
        if self.type == "liquid" and self.clean_count != float('inf') and self.clean_count > 0:
            canvas.create_text(self.centreX, self.centreY,
                               text=str(self.clean_count),
                               fill="black", font=("Arial", 8, "bold"),
                               tags=self.name)

        # 杂物显示特殊标记
        if self.type == "debris":
            canvas.create_text(self.centreX, self.centreY,
                               text="X", fill="red", font=("Arial", 10, "bold"),
                               tags=self.name)

        return body

    def _get_color_by_type(self):
        """根据垃圾类型返回不同的颜色"""
        colors = {
            "dust": "lightgray",
            "crumb": "brown",
            "paper": "white",
            "liquid": "lightblue",
            "hair": "darkgray",
            "debris": "gray"
        }
        return colors.get(self.type, "gray")

    def get_message(self):
        message = [self.name, self.centreX, self.centreY, self.type, self.size, self.weight, self.clean_count]
        return message

    def is_cleanable(self):
        """检查垃圾是否可清洁"""
        return self.type != "debris"

    def clean(self, current_time=0):
        """清洁垃圾，返回是否完全清除，current_time为当前帧计数"""
        if self.type == "debris":
            return False  # 杂物无法清洁

        # 检查冷却时间
        if current_time - self.last_clean_time < self.clean_cooldown:
            return False  # 冷却中，不能清洁

        self.last_clean_time = current_time
        self.clean_count -= 1

        if self.clean_count <= 0:
            return True  # 清洁完成
        return False  # 还需要继续清洁