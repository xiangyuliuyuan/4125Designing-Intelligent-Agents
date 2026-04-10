import random

from app.logging_config import get_logger, log_event
from robot.state_view import derive_bot_mode

logger = get_logger(__name__)


class PotentialFieldBrain:
    def __init__(self, botp):
        self.bot = botp

        # Wandering state (used when no significant forces)
        self.turningCount = 0
        self.movingCount = random.randrange(50, 100)
        self.currentlyTurning = False

        # Overlap handling (backing away from overlapping bots)
        self.isOverlapping = False
        self.overlapCount = 0
        self.overlap_direction = 0
        self.overlap_threshold = 20000
        self.overlap_back_frames = 15

        # State flags needed by derive_bot_mode / external code
        self.isAvoiding = False
        self.isAvoidingDebris = False
        self.isAvoidingCat = False
        self.is_cat_frozen = False
        self.force_cat_freeze = False

        # Cat thresholds
        self.cat_avoid_threshold = 400
        self.cat_freeze_threshold = 3000

        # APF thresholds
        self.debris_repulse_threshold = 3000
        self.bot_repulse_threshold = 3000

        # Debris hard avoidance state machine (like Subsumption)
        self.debris_avoid_active = False
        self.debris_avoid_counter = 0
        self.debris_avoid_direction = 1
        self.debris_hard_threshold = 5000
        self.debris_hard_frames = 18

        # Turn smoothing (dampen frame-to-frame oscillation)
        self._smooth_turn = 0.0

        # Debug logging throttle
        self.debug_counter = 0

    # ------------------------------------------------------------------
    # Force computation helpers
    # ------------------------------------------------------------------

    def _attractive_force_light(self, lightL, lightR):
        """Attractive force toward light (dirt areas). Returns turn signal."""
        diff = lightR - lightL
        magnitude = abs(diff)
        if magnitude < 50:
            return 0.0
        # Normalize: stronger difference = stronger turn signal, capped
        force = max(-1.0, min(1.0, diff / 1000.0))
        return force

    def _attractive_force_charger(self, chargerL, chargerR, weight):
        """Attractive force toward charger. Returns turn signal."""
        diff = chargerR - chargerL
        magnitude = abs(diff)
        if magnitude < 20:
            return 0.0
        force = max(-1.0, min(1.0, diff / 500.0))
        return force * weight

    def _repulsive_force_cat(self, catL, catR):
        """Repulsive force away from cat. Returns turn signal."""
        cat_sum = catL + catR
        if cat_sum <= self.cat_avoid_threshold:
            return 0.0
        # Turn away from stronger signal
        diff = catL - catR  # positive = cat on left, turn right (negative turn)
        if abs(diff) < 10:
            diff = random.choice([-100, 100])
        strength = min(cat_sum / 3000.0, 3.0)
        force = max(-1.0, min(1.0, diff / max(abs(diff), 1))) * strength
        # Negative diff means cat on right -> turn left (positive),
        # but we want to flee, so: cat on left -> turn right (negative)
        return -force

    def _repulsive_force_debris(self, debrisL, debrisR):
        """Repulsive force away from debris. Returns turn signal."""
        debris_sum = debrisL + debrisR
        if debris_sum <= self.debris_repulse_threshold:
            return 0.0
        diff = debrisL - debrisR
        if abs(diff) < 10:
            diff = random.choice([-100, 100])
        strength = min(debris_sum / 6000.0, 2.0)
        force = max(-1.0, min(1.0, diff / max(abs(diff), 1))) * strength
        return -force

    def _repulsive_force_bot(self, botL, botR):
        """Repulsive force away from other bots. Returns turn signal."""
        bot_sum = botL + botR
        if bot_sum <= self.bot_repulse_threshold:
            return 0.0
        diff = botL - botR
        if abs(diff) < 10:
            diff = random.choice([-100, 100])
        strength = min(bot_sum / 6000.0, 2.0)
        force = max(-1.0, min(1.0, diff / max(abs(diff), 1))) * strength
        return -force

    # ------------------------------------------------------------------
    # Main decision method
    # ------------------------------------------------------------------

    def thinkAndAct(
        self,
        lightL,
        lightR,
        chargerL,
        chargerR,
        x,
        y,
        sl,
        sr,
        battery,
        debrisL=0,
        debrisR=0,
        botL=0,
        botR=0,
        catL=0,
        catR=0,
    ):
        newX = None
        newY = None

        forced_cat_freeze = self.force_cat_freeze
        was_overlapping = self.isOverlapping
        was_cat_frozen = self.is_cat_frozen and not forced_cat_freeze
        was_avoiding_cat = self.isAvoidingCat

        bot_sum = botL + botR
        debris_sum = debrisL + debrisR
        cat_sum = catL + catR
        is_overlap = bot_sum > self.overlap_threshold

        # Reset per-frame state
        self.is_cat_frozen = False
        self.isAvoidingCat = False
        self.isAvoiding = False
        self.isAvoidingDebris = False

        # Debug logging
        self.debug_counter += 1
        if self.debug_counter >= 30:
            if bot_sum > 5000 or debris_sum > 5000 or cat_sum > self.cat_avoid_threshold:
                log_event(
                    "DEBUG",
                    logger,
                    event="bot.sensor_scan",
                    bot=self.bot.name,
                    mode=derive_bot_mode(self.bot),
                    bot_signal=bot_sum,
                    cat_signal=cat_sum,
                    debris_signal=debris_sum,
                    overlap=is_overlap,
                )
            self.debug_counter = 0

        base_speed = 5.0
        speedLeft = base_speed
        speedRight = base_speed

        # --- Priority 1: Queuing at charger (stop) ---
        if getattr(self.bot, "queuing_at_charger", False):
            speedLeft = 0.0
            speedRight = 0.0
            if self.isOverlapping:
                self.isOverlapping = False
                self.overlapCount = 0
            return speedLeft, speedRight, newX, newY

        # --- Priority 2: Bot overlap (back away) ---
        if is_overlap or self.isOverlapping:
            if not self.isOverlapping:
                self.isOverlapping = True
                self.overlapCount = self.overlap_back_frames
                self.overlap_direction = random.choice([-1, 1])
                log_event(
                    "INFO",
                    logger,
                    event="bot.overlap_started",
                    bot=self.bot.name,
                    mode="overlap",
                    reason="bot_signal_threshold",
                    bot_signal=bot_sum,
                )

            if self.overlapCount > 0:
                turn = random.uniform(-1.0, 1.0)
                speedLeft = -5.0 + turn
                speedRight = -5.0 - turn
                self.overlapCount -= 1
            else:
                self.isOverlapping = False
                log_event(
                    "INFO",
                    logger,
                    event="bot.overlap_resolved",
                    bot=self.bot.name,
                    mode=derive_bot_mode(self.bot),
                    reason="separation_complete",
                )
                speedLeft = base_speed
                speedRight = base_speed

            self._log_cat_transitions(was_cat_frozen, was_avoiding_cat, cat_sum)
            return speedLeft, speedRight, newX, newY

        # --- Priority 3: Cat freeze (forced or very close cat) ---
        if forced_cat_freeze or cat_sum > self.cat_freeze_threshold:
            self.is_cat_frozen = True
            speedLeft = 0.0
            speedRight = 0.0
            self._log_cat_transitions(was_cat_frozen, was_avoiding_cat, cat_sum)
            return speedLeft, speedRight, newX, newY

        # --- Priority 4: Hard debris avoidance (state machine) ---
        if debris_sum > self.debris_hard_threshold or self.debris_avoid_active:
            if not self.debris_avoid_active:
                self.debris_avoid_active = True
                self.debris_avoid_counter = self.debris_hard_frames
                if debrisL > debrisR:
                    self.debris_avoid_direction = -1  # turn right
                elif debrisR > debrisL:
                    self.debris_avoid_direction = 1   # turn left
                else:
                    self.debris_avoid_direction = random.choice([-1, 1])
                log_event(
                    "DEBUG",
                    logger,
                    event="bot.debris_avoid_started",
                    bot=self.bot.name,
                    mode="avoid_debris",
                    reason="debris_detected",
                    debris_signal=debris_sum,
                )

            if self.debris_avoid_counter > 0:
                self.isAvoidingDebris = True
                if self.debris_avoid_direction >= 0:
                    speedLeft = 3.0
                    speedRight = -3.0
                else:
                    speedLeft = -3.0
                    speedRight = 3.0
                self.debris_avoid_counter -= 1
            else:
                self.debris_avoid_active = False
                self.isAvoidingDebris = False

            if not self.debris_avoid_active or self.debris_avoid_counter <= 0:
                self.debris_avoid_active = False
            else:
                self._log_cat_transitions(was_cat_frozen, was_avoiding_cat, cat_sum)
                return speedLeft, speedRight, newX, newY

        # --- APF force summation ---
        net_turn = 0.0
        forward_scale = 1.0

        # Attractive: light (dirt)
        light_force = self._attractive_force_light(lightL, lightR)
        net_turn += light_force

        # Attractive: charger (weighted heavily when battery low)
        charger_weight = 1.0
        if battery < self.bot.battery_low_threshold:
            charger_weight = 10.0
        charger_force = self._attractive_force_charger(chargerL, chargerR, charger_weight)
        net_turn += charger_force

        # Repulsive: cat
        cat_force = self._repulsive_force_cat(catL, catR)
        if cat_sum > self.cat_avoid_threshold:
            self.isAvoidingCat = True
            net_turn += cat_force * 8.0
            forward_scale = min(forward_scale, 0.3)

        # Repulsive: debris (soft force, complements hard avoidance above)
        debris_force = self._repulsive_force_debris(debrisL, debrisR)
        if debris_sum > self.debris_repulse_threshold:
            self.isAvoidingDebris = True
            net_turn += debris_force * 4.0
            forward_scale = min(forward_scale, 0.4)

        # Repulsive: other bots
        bot_force = self._repulsive_force_bot(botL, botR)
        if bot_sum > self.bot_repulse_threshold:
            self.isAvoiding = True
            net_turn += bot_force * 1.5
            forward_scale = min(forward_scale, 0.7)

        # --- Smooth turn signal to prevent jittering ---
        self._smooth_turn = 0.6 * self._smooth_turn + 0.4 * net_turn
        net_turn = self._smooth_turn

        # --- Convert net force to wheel speeds ---
        has_significant_force = (
            self.isAvoidingCat
            or self.isAvoidingDebris
            or self.isAvoiding
            or abs(light_force) > 0.1
            or abs(charger_force) > 0.1
        )

        if battery < self.bot.battery_low_threshold and abs(charger_force) > 0.05:
            speed = 3.0
            turn_modifier = net_turn * 3.0
            speedLeft = speed + turn_modifier
            speedRight = speed - turn_modifier
            speedLeft = max(-5.0, min(5.0, speedLeft))
            speedRight = max(-5.0, min(5.0, speedRight))

        elif has_significant_force:
            speed = base_speed * forward_scale
            turn_modifier = net_turn * 3.0
            speedLeft = speed + turn_modifier
            speedRight = speed - turn_modifier
            speedLeft = max(-5.0, min(8.0, speedLeft))
            speedRight = max(-5.0, min(8.0, speedRight))

        else:
            if self.currentlyTurning:
                speedLeft = -2.0
                speedRight = 2.0
                self.turningCount -= 1
                if self.turningCount <= 0:
                    self.currentlyTurning = False
                    self.movingCount = random.randrange(50, 100)
            else:
                speedLeft = base_speed
                speedRight = base_speed
                self.movingCount -= 1
                if self.movingCount <= 0:
                    self.currentlyTurning = True
                    self.turningCount = random.randrange(20, 40)

        self._log_cat_transitions(was_cat_frozen, was_avoiding_cat, cat_sum)
        return speedLeft, speedRight, newX, newY

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def _log_cat_transitions(self, was_cat_frozen, was_avoiding_cat, cat_sum):
        """Log cat-related state transitions."""
        if self.is_cat_frozen and not was_cat_frozen:
            log_event(
                "INFO",
                logger,
                event="bot.cat_freeze_started",
                bot=self.bot.name,
                mode="cat_freeze",
                reason="cat_too_close",
                cat_signal=cat_sum,
            )
        elif was_cat_frozen and not self.is_cat_frozen:
            log_event(
                "INFO",
                logger,
                event="bot.cat_freeze_resolved",
                bot=self.bot.name,
                mode=derive_bot_mode(self.bot),
                reason="cat_signal_reduced"
                if cat_sum <= self.cat_freeze_threshold
                else "higher_priority_behavior",
                cat_signal=cat_sum,
            )

        if self.isAvoidingCat and not was_avoiding_cat:
            log_event(
                "INFO",
                logger,
                event="bot.cat_avoid_started",
                bot=self.bot.name,
                mode="avoid_cat",
                reason="cat_detected",
                cat_signal=cat_sum,
            )
        elif was_avoiding_cat and not self.isAvoidingCat:
            log_event(
                "INFO",
                logger,
                event="bot.cat_avoid_resolved",
                bot=self.bot.name,
                mode=derive_bot_mode(self.bot),
                reason="cat_signal_cleared",
            )
