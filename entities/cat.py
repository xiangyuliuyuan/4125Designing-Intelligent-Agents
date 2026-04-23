import math
import random

from app.logging_config import get_logger, log_event
from entities import dirt
from robot.state_view import derive_cat_mode
from ui import renderer

logger = get_logger(__name__)

WORLD_SIZE = 1000
CAT_COLLISION_RADIUS = 15.0


class Cat:
    def __init__(self, namep):
        self.name = namep
        self.x = random.randint(100, 900)
        self.y = random.randint(100, 900)
        self.theta = random.uniform(0.0, 2.0 * math.pi)
        self.speed = 5.0
        self.avoid_distance = 100
        self.panic_distance = 80

        self.turningCount = 0
        self.movingCount = random.randrange(50, 100)
        self.currentlyTurning = False

        self.avoidCount = 0
        self.isAvoiding = False
        self.avoidDirection = 0
        self.total_turn_frames = 22

        self.isJumping = False
        self.jump_frames = 0
        self.last_logged_mode = None

    def draw(self, canvas):
        renderer.draw_cat(canvas, self)

    def _wrapped_delta(self, target, current):
        delta = target - current
        half_world = WORLD_SIZE / 2
        if delta > half_world:
            delta -= WORLD_SIZE
        elif delta < -half_world:
            delta += WORLD_SIZE
        return delta

    def _wrapped_vector_to_bot(self, bot):
        return self._wrapped_delta(bot.x, self.x), self._wrapped_delta(bot.y, self.y)

    def _bot_agents(self, agents):
        return [agent for agent in agents if hasattr(agent, 'brain') and hasattr(agent, 'battery')]

    def _wrapped_distance_to_point(self, point_x, point_y, bot):
        dx = self._wrapped_delta(bot.x, point_x)
        dy = self._wrapped_delta(bot.y, point_y)
        return math.sqrt(dx * dx + dy * dy)

    def _minimum_distance_to_bots(self, point_x, point_y, bots):
        nearest_bot = None
        min_distance = float("inf")

        for bot in bots:
            distance = self._wrapped_distance_to_point(point_x, point_y, bot)
            if distance < min_distance:
                min_distance = distance
                nearest_bot = bot

        return nearest_bot, min_distance

    def _clamp_jump_position(self, new_x, new_y):
        clamped_x = max(renderer.CAT_JUMP_HORIZONTAL_MARGIN, min(WORLD_SIZE - renderer.CAT_JUMP_HORIZONTAL_MARGIN, new_x))
        clamped_y = max(renderer.CAT_JUMP_TOP_MARGIN, min(WORLD_SIZE - renderer.CAT_JUMP_HORIZONTAL_MARGIN, new_y))
        return clamped_x, clamped_y

    @staticmethod
    def _get_debris(passiveObjects):
        return [
            obj for obj in passiveObjects
            if isinstance(obj, (dirt.plusDirt, dirt.Dirt))
            and getattr(obj, "type", None) == "debris"
        ]

    @staticmethod
    def _collides_with_debris(px, py, debris_list):
        half = WORLD_SIZE / 2
        for obj in debris_list:
            ox, oy = obj.getLocation()
            radius = CAT_COLLISION_RADIUS + getattr(obj, "size", 0)
            dx = px - ox
            dy = py - oy
            if dx > half:
                dx -= WORLD_SIZE
            elif dx < -half:
                dx += WORLD_SIZE
            if dy > half:
                dy -= WORLD_SIZE
            elif dy < -half:
                dy += WORLD_SIZE
            if dx * dx + dy * dy < radius * radius:
                return True
        return False

    def _select_jump_landing(self, base_angle, base_distance, bots, debris_list=()):
        angle_offsets = (
            0.0,
            math.pi / 6,
            -math.pi / 6,
            math.pi / 3,
            -math.pi / 3,
            math.pi / 2,
            -math.pi / 2,
            (2 * math.pi) / 3,
            -(2 * math.pi) / 3,
            (5 * math.pi) / 6,
            -(5 * math.pi) / 6,
            math.pi,
        )
        candidate_distances = []
        for candidate_distance in (
            base_distance,
            min(200.0, base_distance + 25.0),
            min(200.0, base_distance + 50.0),
            max(100.0, base_distance - 25.0),
        ):
            if candidate_distance not in candidate_distances:
                candidate_distances.append(candidate_distance)

        best_safe = None
        best_overall = None

        for candidate_distance in candidate_distances:
            for angle_offset in angle_offsets:
                angle = base_angle + angle_offset
                candidate_x = self.x + math.cos(angle) * candidate_distance
                candidate_y = self.y + math.sin(angle) * candidate_distance
                candidate_x, candidate_y = self._clamp_jump_position(candidate_x, candidate_y)
                _nearest_bot, clearance = self._minimum_distance_to_bots(candidate_x, candidate_y, bots)
                on_debris = self._collides_with_debris(candidate_x, candidate_y, debris_list)
                # Prefer debris-free landings: (not on debris) sorts higher than (on debris)
                score = (not on_debris, clearance, -abs(angle_offset), candidate_distance)
                candidate = (score, candidate_x, candidate_y)

                if best_overall is None or score > best_overall[0]:
                    best_overall = candidate

                if clearance >= self.panic_distance and not on_debris and (best_safe is None or score > best_safe[0]):
                    best_safe = candidate

        chosen = best_safe or best_overall
        return chosen[1], chosen[2]

    def jump_away(self, agents, passiveObjects=()):
        if self.isJumping:
            return

        bots = self._bot_agents(agents)
        nearest_bot, min_distance = self._minimum_distance_to_bots(self.x, self.y, bots)
        debris_list = self._get_debris(passiveObjects)

        if nearest_bot:
            bot_dx, bot_dy = self._wrapped_vector_to_bot(nearest_bot)
            dx = -bot_dx
            dy = -bot_dy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                angle = math.atan2(dy, dx) + random.uniform(-0.5, 0.5)
            else:
                angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(100, 200)

            self.x, self.y = self._select_jump_landing(angle, distance, bots, debris_list)

            self.isJumping = True
            self.jump_frames = 10
            self._log_mode_change("panic_jump_started", nearest_bot=nearest_bot.name, distance=min_distance)

    def _nearest_bot_info(self, agents):
        return self._minimum_distance_to_bots(self.x, self.y, self._bot_agents(agents))

    def _log_mode_change(self, reason, **extra_fields):
        new_mode = derive_cat_mode(self)
        if new_mode != self.last_logged_mode:
            log_event(
                "INFO",
                logger,
                event="cat.mode_change",
                cat=self.name,
                from_mode=self.last_logged_mode or "none",
                to_mode=new_mode,
                reason=reason,
                **extra_fields,
            )
            self.last_logged_mode = new_mode

    def update(self, canvas, agents, dt, passiveObjects=()):
        nearest_bot, min_distance = self._nearest_bot_info(agents)
        was_avoiding = self.isAvoiding

        # Panic jump must run before the older collision-distance logic;
        # once a bot gets this close, the cat should immediately disengage.
        if nearest_bot and min_distance < self.panic_distance:
            log_event(
                "INFO",
                logger,
                event="cat.panic_jump",
                cat=self.name,
                mode="panic_jump",
                reason="bot_too_close",
                nearest_bot=nearest_bot.name,
                distance=min_distance,
            )
            self.jump_away(agents, passiveObjects)

        if self.isJumping:
            self.jump_frames -= 1
            if self.jump_frames <= 0:
                self.isJumping = False
                self._log_mode_change("panic_jump_completed")
            canvas.delete(self.name)
            self.draw(canvas)
            return

        if not nearest_bot or min_distance >= self.avoid_distance:
            nearest_bot = None

        if nearest_bot:
            if self.isAvoiding:
                if self.avoidCount > 0:
                    if self.avoidDirection == 1:
                        self.theta -= 0.1 * dt
                    else:
                        self.theta += 0.1 * dt
                    self.avoidCount -= 1

                    if self.avoidCount <= 0:
                        self.isAvoiding = False
                        log_event(
                            "DEBUG",
                            logger,
                            event="cat.turn_completed",
                            cat=self.name,
                            mode=derive_cat_mode(self),
                            reason="rotation_finished",
                        )
                        self.movingCount = random.randrange(50, 100)
                        self.currentlyTurning = False
                else:
                    self.isAvoiding = False
                    self.movingCount = random.randrange(50, 100)
                    self.currentlyTurning = False
            else:
                self.isAvoiding = True
                self.avoidCount = self.total_turn_frames
                bot_dx, bot_dy = self._wrapped_vector_to_bot(nearest_bot)
                escape_angle = math.atan2(-bot_dy, -bot_dx)
                self.theta = escape_angle
                log_event(
                    "INFO",
                    logger,
                    event="cat.avoid_started",
                    cat=self.name,
                    mode="avoid_bot",
                    reason="bot_nearby",
                    nearest_bot=nearest_bot.name,
                    distance=min_distance,
                )

                if random.choice([True, False]):
                    self.avoidDirection = 1
                    log_event("DEBUG", logger, event="cat.turn_direction", cat=self.name, direction="left")
                else:
                    self.avoidDirection = -1
                    log_event("DEBUG", logger, event="cat.turn_direction", cat=self.name, direction="right")
        else:
            if self.isAvoiding:
                self.isAvoiding = False
                self.avoidCount = 0
                log_event(
                    "INFO",
                    logger,
                    event="cat.avoid_completed",
                    cat=self.name,
                    mode=derive_cat_mode(self),
                    reason="bot_no_longer_nearby",
                )

            if self.currentlyTurning:
                self.theta -= 0.05 * dt
                self.turningCount -= 1
                if self.turningCount <= 0:
                    self.currentlyTurning = False
                    self.movingCount = random.randrange(50, 100)
            else:
                self.movingCount -= 1
                if self.movingCount <= 0:
                    self.currentlyTurning = True
                    self.turningCount = random.randrange(20, 40)

        new_x = self.x + math.cos(self.theta) * self.speed * dt
        new_y = self.y + math.sin(self.theta) * self.speed * dt

        # Wrap BEFORE collision check so we test the real destination
        if new_x >= WORLD_SIZE:
            new_x -= WORLD_SIZE
        elif new_x < 0:
            new_x += WORLD_SIZE
        if new_y >= WORLD_SIZE:
            new_y -= WORLD_SIZE
        elif new_y < 0:
            new_y += WORLD_SIZE

        debris_list = self._get_debris(passiveObjects)
        # If the cat is already on debris (e.g. landed from a jump or wrapping),
        # always allow movement so it can escape — otherwise it is stuck forever.
        already_on_debris = debris_list and self._collides_with_debris(self.x, self.y, debris_list)
        if debris_list and not already_on_debris and self._collides_with_debris(new_x, new_y, debris_list):
            # Turn away from the obstacle instead of walking through it
            self.theta += math.pi * 0.75 + random.uniform(-0.3, 0.3)
            self.currentlyTurning = True
            self.turningCount = random.randrange(10, 20)
        else:
            self.x = new_x
            self.y = new_y

        if was_avoiding != self.isAvoiding:
            self._log_mode_change("cat_behavior_update")

        canvas.delete(self.name)
        self.draw(canvas)

    def getLocation(self):
        return self.x, self.y
