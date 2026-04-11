"""Coverage-map brain: Subsumption safety stack + memory-guided exploration (RQ5).

Divides the 1000x1000 world into a 50x50 grid and steers toward least-visited
cells when no higher-priority behavior is active.
"""
import math
import random

from app.logging_config import get_logger, log_event
from robot.motion import wrapped_delta as _wrapped_delta
from robot.state_view import derive_bot_mode

logger = get_logger(__name__)

GRID_CELLS = 50
CELL_SIZE = 20  # 1000 / 50


class CoverageMapBrain:
    def __init__(self, botp):
        self.bot = botp

        # Coverage grid: visit counts per cell
        self.coverage_grid = [[0] * GRID_CELLS for _ in range(GRID_CELLS)]
        self._target_cell = None  # (gx, gy) currently steering toward

        # Subsumption state (identical to brain.py)
        self.avoidCount = 0
        self.isAvoiding = False
        self.avoidDirection = 0
        self.turn_angle_sum = 0
        self.full_circle_frames = 88

        self.isOverlapping = False
        self.overlapCount = 0
        self.overlap_direction = 0
        self.overlap_threshold = 20000
        self.overlap_back_frames = 25

        self.isAvoidingDebris = False
        self.debris_avoid_direction = 1
        self.debris_avoid_counter = 0

        self.cat_avoid_threshold = 700
        self.cat_freeze_threshold = 3000
        self.is_cat_frozen = False
        self.force_cat_freeze = False
        self.isAvoidingCat = False
        self.cat_avoid_hold_frames = 25
        self.cat_avoid_hold_remaining = 0
        self.cat_avoid_direction = 1

    # ------------------------------------------------------------------
    # Coverage helpers
    # ------------------------------------------------------------------
    def _update_coverage(self, x, y):
        gx = max(0, min(GRID_CELLS - 1, int(x / CELL_SIZE)))
        gy = max(0, min(GRID_CELLS - 1, int(y / CELL_SIZE)))
        self.coverage_grid[gy][gx] += 1

    def get_coverage_percentage(self):
        """Return fraction of cells visited at least once."""
        visited = sum(1 for row in self.coverage_grid for c in row if c > 0)
        return visited / (GRID_CELLS * GRID_CELLS)

    def _find_least_visited_cell(self, x, y):
        """Find the nearest cell with the minimum visit count, excluding the
        bot's current cell to prevent a self-targeting loop."""
        cur_gx = max(0, min(GRID_CELLS - 1, int(x / CELL_SIZE)))
        cur_gy = max(0, min(GRID_CELLS - 1, int(y / CELL_SIZE)))

        min_visits = float("inf")
        for gy in range(GRID_CELLS):
            for gx in range(GRID_CELLS):
                if (gx, gy) != (cur_gx, cur_gy):
                    if self.coverage_grid[gy][gx] < min_visits:
                        min_visits = self.coverage_grid[gy][gx]

        # Among cells with min_visits, find the nearest one
        best = None
        best_dist_sq = float("inf")
        for gy in range(GRID_CELLS):
            for gx in range(GRID_CELLS):
                if (gx, gy) == (cur_gx, cur_gy):
                    continue
                if self.coverage_grid[gy][gx] == min_visits:
                    cx = gx * CELL_SIZE + CELL_SIZE / 2
                    cy = gy * CELL_SIZE + CELL_SIZE / 2
                    dx = _wrapped_delta(cx, x)
                    dy = _wrapped_delta(cy, y)
                    d2 = dx * dx + dy * dy
                    if d2 < best_dist_sq:
                        best_dist_sq = d2
                        best = (gx, gy)

        return best

    def _steer_toward_cell(self, target_gx, target_gy, x, y):
        """Return (speedLeft, speedRight) to steer toward target cell centre."""
        tx = target_gx * CELL_SIZE + CELL_SIZE / 2
        ty = target_gy * CELL_SIZE + CELL_SIZE / 2
        dx = _wrapped_delta(tx, x)
        dy = _wrapped_delta(ty, y)
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < CELL_SIZE:
            # Arrived at target cell, pick a new one
            self._target_cell = None
            return 5.0, 5.0

        # Desired heading angle
        target_angle = math.atan2(dy, dx)
        # Bot heading (theta is already in radians)
        bot_angle = getattr(self.bot, 'theta', 0)

        # Angular error
        angle_err = target_angle - bot_angle
        # Normalise to [-pi, pi]
        while angle_err > math.pi:
            angle_err -= 2 * math.pi
        while angle_err < -math.pi:
            angle_err += 2 * math.pi

        # Proportional steering
        base_speed = 5.0
        turn = max(-1.0, min(1.0, angle_err / (math.pi / 4)))  # normalise
        speedLeft = base_speed + turn * 3.0
        speedRight = base_speed - turn * 3.0
        return max(-5.0, min(8.0, speedLeft)), max(-5.0, min(8.0, speedRight))

    # ------------------------------------------------------------------
    # Main decision method (Subsumption + coverage-guided default)
    # ------------------------------------------------------------------
    def thinkAndAct(self, lightL, lightR, chargerL, chargerR, x, y, sl, sr,
                    battery, debrisL=0, debrisR=0, botL=0, botR=0,
                    catL=0, catR=0):
        newX = None
        newY = None

        # Update coverage map with current position
        self._update_coverage(x, y)

        bot_sum = botL + botR
        debris_sum = debrisL + debrisR
        cat_sum = catL + catR
        is_overlap = bot_sum > self.overlap_threshold
        self.is_cat_frozen = False
        self.isAvoidingCat = False

        speedLeft = 5.0
        speedRight = 5.0

        # --- Priority 1: Charger queuing ---
        if getattr(self.bot, "queuing_at_charger", False):
            speedLeft = 0.0
            speedRight = 0.0
            if self.isOverlapping:
                self.isOverlapping = False
                self.overlapCount = 0
            return speedLeft, speedRight, newX, newY

        # --- Priority 2: Bot overlap ---
        if is_overlap or self.isOverlapping:
            if self.isAvoiding:
                self.isAvoiding = False
                self.avoidCount = 0
                self.turn_angle_sum = 0
            if self.isAvoidingDebris:
                self.isAvoidingDebris = False
            if not self.isOverlapping:
                self.isOverlapping = True
                self.overlapCount = 15
                self.overlap_direction = random.choice([-1, 1])
            if self.overlapCount > 0:
                turn = random.uniform(-1.0, 1.0)
                speedLeft = -5.0 + turn
                speedRight = -5.0 - turn
                self.overlapCount -= 1
            else:
                self.isOverlapping = False
                speedLeft = 5.0
                speedRight = 5.0
            return speedLeft, speedRight, newX, newY

        # --- Priority 3: Low battery ---
        if battery < self.bot.battery_low_threshold:
            if self.isAvoiding:
                self.isAvoiding = False
                self.avoidCount = 0
            if self.isAvoidingDebris:
                self.isAvoidingDebris = False
            speedLeft = 3.0
            speedRight = 3.0
            return speedLeft, speedRight, newX, newY

        # --- Priority 4: Cat freeze ---
        if self.force_cat_freeze or cat_sum > self.cat_freeze_threshold:
            self.is_cat_frozen = True
            if self.isAvoiding:
                self.isAvoiding = False
                self.avoidCount = 0
            if self.isAvoidingDebris:
                self.isAvoidingDebris = False
            self.isAvoidingCat = False
            self.cat_avoid_hold_remaining = 0
            return 0.0, 0.0, newX, newY

        # --- Priority 5: Cat avoidance ---
        if cat_sum > self.cat_avoid_threshold:
            self.isAvoidingCat = True
            self.cat_avoid_hold_remaining = self.cat_avoid_hold_frames
            if self.isAvoiding:
                self.isAvoiding = False
                self.avoidCount = 0
            if self.isAvoidingDebris:
                self.isAvoidingDebris = False
            stronger = max(catL, catR)
            if stronger <= 0:
                speedLeft, speedRight = 3.0, -3.0
            elif abs(catL - catR) <= stronger * 0.15:
                if self.cat_avoid_direction >= 0:
                    self.cat_avoid_direction = 1
                    speedLeft, speedRight = 3.0, -3.0
                else:
                    self.cat_avoid_direction = -1
                    speedLeft, speedRight = -3.0, 3.0
            elif catL > catR:
                self.cat_avoid_direction = 1
                speedLeft, speedRight = 3.0, -3.0
            else:
                self.cat_avoid_direction = -1
                speedLeft, speedRight = -3.0, 3.0
            return speedLeft, speedRight, newX, newY

        elif self.cat_avoid_hold_remaining > 0:
            self.cat_avoid_hold_remaining -= 1
            if self.cat_avoid_hold_remaining <= 0:
                self.isAvoidingCat = False
                speedLeft, speedRight = 5.0, 5.0
            else:
                self.isAvoidingCat = True
                if self.cat_avoid_direction >= 0:
                    speedLeft, speedRight = 3.0, -3.0
                else:
                    speedLeft, speedRight = -3.0, 3.0
            return speedLeft, speedRight, newX, newY

        # --- Priority 6: Debris avoidance ---
        if debris_sum > 5000 or self.isAvoidingDebris:
            if not self.isAvoidingDebris:
                self.isAvoidingDebris = True
                self.debris_avoid_counter = 0
                if debrisL > debrisR:
                    self.debris_avoid_direction = -1
                elif debrisR > debrisL:
                    self.debris_avoid_direction = 1
            if self.debris_avoid_direction >= 0:
                speedLeft, speedRight = 3.0, -3.0
            else:
                speedLeft, speedRight = -3.0, 3.0
            self.debris_avoid_counter += 1
            if debris_sum <= 3000:
                self.isAvoidingDebris = False
                self.debris_avoid_counter = 0
                speedLeft, speedRight = 5.0, 5.0
            return speedLeft, speedRight, newX, newY

        # --- Priority 7: Bot avoidance ---
        if self.isAvoiding:
            if bot_sum <= 3000:
                self.isAvoiding = False
                self.turn_angle_sum = 0
            else:
                if self.avoidDirection == 1:
                    speedLeft, speedRight = 3.0, -3.0
                else:
                    speedLeft, speedRight = -3.0, 3.0
                self.turn_angle_sum += 1
                if self.turn_angle_sum >= self.full_circle_frames:
                    self.avoidDirection = -self.avoidDirection
                    self.turn_angle_sum = 0
                return speedLeft, speedRight, newX, newY

        elif bot_sum > 3000:
            self.isAvoiding = True
            self.turn_angle_sum = 0
            self.avoidDirection = random.choice([-1, 1])
            if self.avoidDirection == 1:
                speedLeft, speedRight = 3.0, -3.0
            else:
                speedLeft, speedRight = -3.0, 3.0
            return speedLeft, speedRight, newX, newY

        # --- Default: Coverage-guided exploration ---
        # Find target cell if we don't have one
        if self._target_cell is None:
            self._target_cell = self._find_least_visited_cell(x, y)

        if self._target_cell is not None:
            speedLeft, speedRight = self._steer_toward_cell(
                self._target_cell[0], self._target_cell[1], x, y
            )
        else:
            # Fallback: random wandering (should not happen)
            speedLeft, speedRight = 5.0, 5.0

        return speedLeft, speedRight, newX, newY
