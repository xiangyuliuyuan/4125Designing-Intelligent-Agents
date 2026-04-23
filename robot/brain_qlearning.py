import json
import random
from collections import defaultdict

from app.logging_config import get_logger, log_event
from robot.state_view import derive_bot_mode

logger = get_logger(__name__)

# Action constants
FORWARD = 0
TURN_LEFT = 1
TURN_RIGHT = 2
SLOW_FORWARD = 3
SEEK_LIGHT_LEFT = 4
SEEK_LIGHT_RIGHT = 5
STOP = 6

NUM_ACTIONS = 7

ACTION_SPEEDS = {
    FORWARD: (5, 5),
    TURN_LEFT: (-2, 2),
    TURN_RIGHT: (2, -2),
    SLOW_FORWARD: (3, 3),
    SEEK_LIGHT_LEFT: (3, 5),
    SEEK_LIGHT_RIGHT: (5, 3),
    STOP: (0.0, 0.0),
}


class QLearningBrain:
    def __init__(self, botp, alpha=0.1, gamma=0.95, epsilon=1.0,
                 epsilon_min=0.05, epsilon_decay=0.995):
        self.bot = botp
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay

        self.q_table = defaultdict(float)
        self.training = False

        # Episode tracking
        self.last_state = None
        self.last_action = None
        self.pending_reward = 0.0

        # Compatibility attributes (needed by derive_bot_mode and bot.py)
        self.force_cat_freeze = False
        self.is_cat_frozen = False
        self.isOverlapping = False
        self.isAvoiding = False
        self.isAvoidingDebris = False
        self.isAvoidingCat = False
        self.cat_avoid_hold_remaining = 0
        self.overlapCount = 0

        # Debris avoidance state machine
        self._debris_avoid_active = False
        self._debris_avoid_counter = 0
        self._debris_avoid_direction = 1
        self._debris_back_frames = 5
        self._debris_turn_frames = 18

        # Softer overlap separation (see brain.py for rationale).
        self.overlap_back_frames = 8
        self.overlap_back_speed = 3.0

    def _reset_q_tracking(self):
        """Reset Q-learning tracking state so accumulated rewards don't leak
        across safety override frames."""
        self.last_state = None
        self.last_action = None
        self.pending_reward = 0.0

    def _discretize_state(self, lightL, lightR, chargerL, chargerR, battery,
                          debrisL, debrisR, botL, botR, catL, catR):
        # Light direction
        if lightL + lightR < 1:
            light_dir = "none"
        elif abs(lightL - lightR) < max(lightL, lightR) * 0.15:
            light_dir = "balanced"
        elif lightL > lightR:
            light_dir = "left"
        else:
            light_dir = "right"

        # Charger direction
        if chargerL + chargerR < 1:
            charger_dir = "none"
        elif abs(chargerL - chargerR) < max(chargerL, chargerR) * 0.15:
            charger_dir = "balanced"
        elif chargerL > chargerR:
            charger_dir = "left"
        else:
            charger_dir = "right"

        # Battery level (4 granular buckets aligned with bot.battery_low_threshold=600)
        if battery > 800:
            battery_level = "high"
        elif battery > 600:
            battery_level = "medium"
        elif battery > 300:
            battery_level = "low"
        else:
            battery_level = "critical"

        # Cat danger
        cat_sum = catL + catR
        if cat_sum > 3000:
            cat_danger = "high"
        elif cat_sum > 700:
            cat_danger = "medium"
        else:
            cat_danger = "low"

        # Debris danger
        debris_sum = debrisL + debrisR
        if debris_sum > 5000:
            debris_danger = "high"
        else:
            debris_danger = "low"

        # Bot danger
        bot_sum = botL + botR
        if bot_sum > 3000:
            bot_danger = "high"
        else:
            bot_danger = "low"

        return (light_dir, charger_dir, battery_level, cat_danger,
                debris_danger, bot_danger)

    def _select_action(self, state):
        if self.training and random.random() < self.epsilon:
            return random.randint(0, NUM_ACTIONS - 1)
        # Greedy: pick action with highest Q-value
        q_values = [self.q_table[(state, a)] for a in range(NUM_ACTIONS)]
        max_q = max(q_values)
        # Break ties randomly
        best_actions = [a for a in range(NUM_ACTIONS) if q_values[a] == max_q]
        return random.choice(best_actions)

    def _action_to_speeds(self, action):
        return ACTION_SPEEDS[action]

    def give_reward(self, reward):
        self.pending_reward += reward

    def end_episode(self):
        if self.training and self.last_state is not None and self.last_action is not None:
            key = (self.last_state, self.last_action)
            self.q_table[key] += self.alpha * (self.pending_reward - self.q_table[key])
        self.last_state = None
        self.last_action = None
        self.pending_reward = 0.0

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def set_training(self, mode):
        self.training = mode

    def save_qtable(self, filepath):
        serializable = {}
        for (state, action), value in self.q_table.items():
            key_str = json.dumps([list(state), action])
            serializable[key_str] = value
        with open(filepath, "w") as f:
            json.dump(serializable, f)

    def load_qtable(self, filepath):
        with open(filepath, "r") as f:
            data = json.load(f)
        self.q_table = defaultdict(float)
        for key_str, value in data.items():
            parsed = json.loads(key_str)
            state = tuple(parsed[0])
            action = parsed[1]
            self.q_table[(state, action)] = value

    def thinkAndAct(self, lightL, lightR, chargerL, chargerR, x, y, sl, sr,
                    battery, debrisL=0, debrisR=0, botL=0, botR=0,
                    catL=0, catR=0):
        newX = None
        newY = None

        bot_sum = botL + botR

        debris_sum = debrisL + debrisR
        cat_sum = catL + catR

        # --- Safety overrides (before Q-learning) ---

        # 0. Charger queuing: stop in place so the bot waits its turn instead
        # of bumping the currently-charging bot. Must precede overlap handling
        # — otherwise the Q-learning bot just backs away and cycles forever.
        if getattr(self.bot, "queuing_at_charger", False):
            if self.isOverlapping:
                self.isOverlapping = False
                self.isAvoiding = False
                self.overlapCount = 0
            self._reset_q_tracking()
            return 0.0, 0.0, newX, newY

        # 1. Cat freeze
        if self.force_cat_freeze:
            self.is_cat_frozen = True
            self._reset_q_tracking()
            return 0.0, 0.0, newX, newY

        # 2. Bot overlap — asymmetric right-of-way to break symmetric deadlock
        if bot_sum > 20000 or self.isOverlapping:
            if self.bot.should_yield_to_nearby_bots():
                if not self.isOverlapping:
                    self.isOverlapping = True
                    self.isAvoiding = True
                    self.overlapCount = self.overlap_back_frames
                self.overlapCount -= 1
                if self.overlapCount <= 0 or bot_sum <= 20000:
                    self.isOverlapping = False
                    self.isAvoiding = False
                else:
                    turn = random.uniform(-0.5, 0.5)
                    self._reset_q_tracking()
                    return (
                        -self.overlap_back_speed + turn,
                        -self.overlap_back_speed - turn,
                        newX,
                        newY,
                    )
            else:
                # Priority side: crawl forward, skip Q-learning for this step.
                if self.isOverlapping:
                    self.isOverlapping = False
                    self.isAvoiding = False
                self._reset_q_tracking()
                return 2.0, 2.0, newX, newY

        # 3. Cat avoidance
        if cat_sum > 3000:
            self.is_cat_frozen = True
            self.isAvoidingCat = True
            self._reset_q_tracking()
            return 0.0, 0.0, newX, newY
        elif cat_sum > 700:
            self.is_cat_frozen = False
            self.isAvoidingCat = True
            self._reset_q_tracking()
            if catL > catR:
                return 3.0, -3.0, newX, newY
            else:
                return -3.0, 3.0, newX, newY
        else:
            self.isAvoidingCat = False
            self.is_cat_frozen = False

        # 4. Debris avoidance - committed state machine
        if debris_sum > 5000 and not self._debris_avoid_active:
            self._debris_avoid_active = True
            total = self._debris_back_frames + self._debris_turn_frames
            self._debris_avoid_counter = total
            if debrisL > debrisR:
                self._debris_avoid_direction = -1  # will turn right
            elif debrisR > debrisL:
                self._debris_avoid_direction = 1   # will turn left
            else:
                self._debris_avoid_direction = random.choice([-1, 1])

        if self._debris_avoid_active:
            self.isAvoidingDebris = True
            if self._debris_avoid_counter > self._debris_turn_frames:
                # Phase 1: back up
                speedLeft = -4.0
                speedRight = -4.0
            else:
                # Phase 2: committed turn
                if self._debris_avoid_direction >= 0:
                    speedLeft = 3.0
                    speedRight = -3.0
                else:
                    speedLeft = -3.0
                    speedRight = 3.0
            self._debris_avoid_counter -= 1
            if self._debris_avoid_counter <= 0:
                self._debris_avoid_active = False
                self.isAvoidingDebris = False
            self._reset_q_tracking()
            return float(speedLeft), float(speedRight), newX, newY

        # Bot avoidance flag for mode/color display (Bug 4)
        self.isAvoiding = bot_sum > 3000

        # --- Q-learning update for previous step ---
        state = self._discretize_state(
            lightL, lightR, chargerL, chargerR, battery,
            debrisL, debrisR, botL, botR, catL, catR
        )

        if self.training and self.last_state is not None and self.last_action is not None:
            # Compute max Q(s', a')
            max_q_next = max(
                self.q_table[(state, a)] for a in range(NUM_ACTIONS)
            )
            key = (self.last_state, self.last_action)
            self.q_table[key] += self.alpha * (
                self.pending_reward + self.gamma * max_q_next - self.q_table[key]
            )
            self.pending_reward = 0.0

        # --- Select and execute action ---
        action = self._select_action(state)
        speedLeft, speedRight = self._action_to_speeds(action)

        # Store for next update
        self.last_state = state
        self.last_action = action

        return float(speedLeft), float(speedRight), newX, newY
