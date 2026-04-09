import heapq
import dirt

class AStar:
    """A*路径规划算法"""

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
        return grid_x * self.grid_size + self.grid_size // 2, grid_y * self.grid_size + self.grid_size // 2

    def _build_obstacle_map(self, passiveObjects, robot_x, robot_y):
        """构建障碍物地图"""
        obstacle_map = [[False for _ in range(self.rows)] for _ in range(self.cols)]

        for obj in passiveObjects:
            # 将垃圾视为障碍物
            if isinstance(obj, dirt.plusDirt) or isinstance(obj, dirt.plusDirt):
                x, y = obj.getLocation()
                grid_x, grid_y = self._get_grid_pos(x, y)
                if 0 <= grid_x < self.cols and 0 <= grid_y < self.rows:
                    obstacle_map[grid_x][grid_y] = True

        return obstacle_map

    def heuristic(self, a, b):
        """启发函数：曼哈顿距离"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def find_path(self, start_x, start_y, target_x, target_y, passiveObjects):
        """
        使用A*算法寻找路径

        Returns:
            path: 路径点列表 [(x1,y1), (x2,y2), ...]，如果没有路径返回None
        """
        start_grid = self._get_grid_pos(start_x, start_y)
        target_grid = self._get_grid_pos(target_x, target_y)

        # 构建障碍物地图
        obstacle_map = self._build_obstacle_map(passiveObjects, start_x, start_y)

        # 如果起点或终点在障碍物上，返回None
        if obstacle_map[start_grid[0]][start_grid[1]] or obstacle_map[target_grid[0]][target_grid[1]]:
            return None

        # A*算法
        open_set = []
        heapq.heappush(open_set, (0, start_grid))
        came_from = {}
        g_score = {start_grid: 0}
        f_score = {start_grid: self.heuristic(start_grid, target_grid)}

        while open_set:
            current = heapq.heappop(open_set)[1]

            if current == target_grid:
                # 重建路径
                path = []
                while current in came_from:
                    path.append(self._get_pixel_pos(current[0], current[1]))
                    current = came_from[current]
                path.append(self._get_pixel_pos(start_grid[0], start_grid[1]))
                path.reverse()
                return path

            # 检查四个方向（上下左右）
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                neighbor = (current[0] + dx, current[1] + dy)

                # 检查边界
                if not (0 <= neighbor[0] < self.cols and 0 <= neighbor[1] < self.rows):
                    continue

                # 检查障碍物
                if obstacle_map[neighbor[0]][neighbor[1]]:
                    continue

                tentative_g = g_score[current] + 1

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self.heuristic(neighbor, target_grid)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return None  # 没有找到路径