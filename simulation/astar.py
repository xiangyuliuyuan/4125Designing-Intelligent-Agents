import heapq
import math
from collections import deque
from entities import dirt


class AStar:
    """A*路径规划算法"""

    ROBOT_CLEARANCE_RADIUS = 30.0

    def __init__(self, width, height, grid_size=10):
        """
        初始化A*算法

        Args:
            width: 地图宽度
            height: 地图高度
            grid_size: 网格大小（每个网格的像素尺寸）
        """
        self.width = width
        self.height = height
        self.grid_size = grid_size
        self.cols = width // grid_size + 1
        self.rows = height // grid_size + 1

    def _get_grid_pos(self, x, y):
        """将像素坐标转换为网格坐标"""
        grid_x = int(x // self.grid_size)
        grid_y = int(y // self.grid_size)
        return max(0, min(grid_x, self.cols - 1)), max(0, min(grid_y, self.rows - 1))

    def _get_pixel_pos(self, grid_x, grid_y):
        """将网格坐标转换为像素坐标（中心点）"""
        pixel_x = min(grid_x * self.grid_size + self.grid_size // 2, self.width)
        pixel_y = min(grid_y * self.grid_size + self.grid_size // 2, self.height)
        return pixel_x, pixel_y

    def _build_obstacle_map(self, passiveObjects, robot_x, robot_y):
        """构建障碍物地图（将 debris 按机器人机身半径做膨胀）"""
        obstacle_map = [[False for _ in range(self.rows)] for _ in range(self.cols)]

        for obj in passiveObjects:
            # 只有 debris（不可清洁杂物）才是真正的障碍物
            if isinstance(obj, (dirt.plusDirt, dirt.Dirt)):
                if hasattr(obj, 'type') and obj.type == 'debris':
                    x, y = obj.getLocation()
                    obstacle_radius = getattr(obj, "size", 0)
                    blocked_radius = self.ROBOT_CLEARANCE_RADIUS + obstacle_radius
                    grid_radius = max(1, math.ceil(blocked_radius / self.grid_size))
                    center_grid_x, center_grid_y = self._get_grid_pos(x, y)

                    for dx in range(-grid_radius, grid_radius + 1):
                        for dy in range(-grid_radius, grid_radius + 1):
                            grid_x = center_grid_x + dx
                            grid_y = center_grid_y + dy
                            if not (0 <= grid_x < self.cols and 0 <= grid_y < self.rows):
                                continue

                            cell_x, cell_y = self._get_pixel_pos(grid_x, grid_y)
                            if math.dist((cell_x, cell_y), (x, y)) <= blocked_radius:
                                obstacle_map[grid_x][grid_y] = True

        return obstacle_map

    _SQRT2 = math.sqrt(2)

    # 8方向移动：上下左右 + 对角线
    _NEIGHBORS = [
        (0, 1, 1.0), (0, -1, 1.0), (1, 0, 1.0), (-1, 0, 1.0),
        (1, 1, _SQRT2), (1, -1, _SQRT2), (-1, 1, _SQRT2), (-1, -1, _SQRT2),
    ]

    def heuristic(self, a, b):
        """启发函数：切比雪夫距离（适配8方向移动）"""
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return max(dx, dy) + (self._SQRT2 - 1) * min(dx, dy)

    def _clear_obstacle_cells(self, obstacle_map, cells):
        for grid_x, grid_y in cells:
            obstacle_map[grid_x][grid_y] = False

    def _reconstruct_path(self, start_grid, target_grid, came_from):
        path = deque()
        current = target_grid
        while current in came_from:
            path.appendleft(self._get_pixel_pos(current[0], current[1]))
            current = came_from[current]
        path.appendleft(self._get_pixel_pos(start_grid[0], start_grid[1]))
        return path

    def find_paths_to_targets(self, start_x, start_y, targets, passiveObjects):
        """
        使用一次多目标搜索计算同一起点到多个目标的可达路径。

        Args:
            targets: 可迭代对象，元素为 (key, target_x, target_y)

        Returns:
            dict[key, deque | None]
        """
        targets = list(targets)
        if not targets:
            return {}

        start_grid = self._get_grid_pos(start_x, start_y)
        target_entries = {}
        for key, target_x, target_y in targets:
            target_grid = self._get_grid_pos(target_x, target_y)
            target_entries.setdefault(target_grid, []).append(key)

        obstacle_map = self._build_obstacle_map(passiveObjects, start_x, start_y)
        self._clear_obstacle_cells(obstacle_map, [start_grid, *target_entries.keys()])

        open_set = []
        heapq.heappush(open_set, (0.0, start_grid))
        came_from = {}
        g_score = {start_grid: 0.0}
        closed_set = set()
        remaining_targets = set(target_entries)

        while open_set and remaining_targets:
            current_cost, current = heapq.heappop(open_set)

            if current in closed_set:
                continue
            closed_set.add(current)

            if current in remaining_targets:
                remaining_targets.remove(current)
                if not remaining_targets:
                    break

            for dx, dy, cost in self._NEIGHBORS:
                neighbor = (current[0] + dx, current[1] + dy)

                if not (0 <= neighbor[0] < self.cols and 0 <= neighbor[1] < self.rows):
                    continue

                if neighbor in closed_set:
                    continue

                if obstacle_map[neighbor[0]][neighbor[1]]:
                    continue

                if dx != 0 and dy != 0:
                    if obstacle_map[current[0] + dx][current[1]] or obstacle_map[current[0]][current[1] + dy]:
                        continue

                tentative_g = g_score[current] + cost
                if tentative_g >= g_score.get(neighbor, math.inf):
                    continue

                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                h = min(self.heuristic(neighbor, t) for t in remaining_targets) if remaining_targets else 0.0
                f = tentative_g + h
                heapq.heappush(open_set, (f, neighbor))

        results = {}
        for target_grid, keys in target_entries.items():
            if target_grid == start_grid:
                path = deque([self._get_pixel_pos(start_grid[0], start_grid[1])])
            elif target_grid in g_score:
                path = self._reconstruct_path(start_grid, target_grid, came_from)
            else:
                path = None

            for key in keys:
                results[key] = deque(path) if path is not None else None

        return results

    def find_path(self, start_x, start_y, target_x, target_y, passiveObjects):
        """
        使用A*算法寻找路径

        Returns:
            path: 路径点列表 deque([(x1,y1), (x2,y2), ...])，如果没有路径返回None
        """
        start_grid = self._get_grid_pos(start_x, start_y)
        target_grid = self._get_grid_pos(target_x, target_y)

        # 构建障碍物地图
        obstacle_map = self._build_obstacle_map(passiveObjects, start_x, start_y)

        # 如果起点或终点在障碍物上，清除该格障碍以允许通过（避免因站在障碍物上而寻路失败）
        self._clear_obstacle_cells(obstacle_map, [start_grid, target_grid])

        # A*算法
        open_set = []
        heapq.heappush(open_set, (0, start_grid))
        came_from = {}
        g_score = {start_grid: 0}
        closed_set = set()

        while open_set:
            _f, current = heapq.heappop(open_set)

            if current == target_grid:
                return self._reconstruct_path(start_grid, target_grid, came_from)

            if current in closed_set:
                continue
            closed_set.add(current)

            # 检查8个方向
            for dx, dy, cost in self._NEIGHBORS:
                neighbor = (current[0] + dx, current[1] + dy)

                # 检查边界
                if not (0 <= neighbor[0] < self.cols and 0 <= neighbor[1] < self.rows):
                    continue

                if neighbor in closed_set:
                    continue

                # 检查障碍物
                if obstacle_map[neighbor[0]][neighbor[1]]:
                    continue

                # 对角线移动时，检查两个正交邻居是否被阻挡（防止穿墙）
                if dx != 0 and dy != 0:
                    if obstacle_map[current[0] + dx][current[1]] or obstacle_map[current[0]][current[1] + dy]:
                        continue

                tentative_g = g_score[current] + cost

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + self.heuristic(neighbor, target_grid)
                    heapq.heappush(open_set, (f, neighbor))

        return None  # 没有找到路径
