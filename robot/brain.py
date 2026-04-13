import random

from app.logging_config import get_logger, log_event
from robot.state_view import derive_bot_mode

logger = get_logger(__name__)


class Brain:
    def __init__(self, botp):
        self.bot = botp
        self.turningCount = 0
        self.movingCount = random.randrange(50, 100)
        self.currentlyTurning = False

        self.avoidCount = 0
        self.isAvoiding = False
        self.avoidDirection = 0
        self.debug_counter = 0
        self.total_turn_frames = 22

        self.turn_angle_sum = 0
        self.full_circle_frames = 88

        self.isOverlapping = False
        self.overlapCount = 0
        self.overlap_direction = 0
        self.overlap_threshold = 20000
        self.overlap_back_frames = 25
        self.overlap_back_speed = 6.0

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
        self.is_cat_frozen = False
        self.isAvoidingCat = False

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

        speedLeft = 5.0
        speedRight = 5.0

        if getattr(self.bot, "queuing_at_charger", False):
            # Bot is queuing at an occupied charger — stop and suppress overlap
            speedLeft = 0.0
            speedRight = 0.0
            if self.isOverlapping:
                self.isOverlapping = False
                self.overlapCount = 0

        elif is_overlap or self.isOverlapping:
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
                speedLeft = 5.0
                speedRight = 5.0

        elif forced_cat_freeze or cat_sum > self.cat_freeze_threshold:
            self.is_cat_frozen = True
            if self.isAvoiding:
                self.isAvoiding = False
                self.avoidCount = 0
            if self.isAvoidingDebris:
                self.isAvoidingDebris = False
            self.isAvoidingCat = False
            self.cat_avoid_hold_remaining = 0
            speedLeft = 0.0
            speedRight = 0.0

        elif cat_sum > self.cat_avoid_threshold:
            self.isAvoidingCat = True
            self.cat_avoid_hold_remaining = self.cat_avoid_hold_frames
            if self.isAvoiding:
                self.isAvoiding = False
                self.avoidCount = 0
            if self.isAvoidingDebris:
                self.isAvoidingDebris = False

            stronger_signal = max(catL, catR)
            if stronger_signal <= 0:
                speedLeft = 3.0
                speedRight = -3.0
            elif abs(catL - catR) <= stronger_signal * 0.15:
                if self.cat_avoid_direction >= 0:
                    self.cat_avoid_direction = 1
                    speedLeft = 3.0
                    speedRight = -3.0
                else:
                    self.cat_avoid_direction = -1
                    speedLeft = -3.0
                    speedRight = 3.0
            elif catL > catR:
                self.cat_avoid_direction = 1
                speedLeft = 3.0
                speedRight = -3.0
            else:
                self.cat_avoid_direction = -1
                speedLeft = -3.0
                speedRight = 3.0

        elif battery < self.bot.battery_low_threshold:
            # Low battery path following should not suppress cat safety.
            # Once cat handling is clear, bot.update() will steer to charger.
            if self.isAvoiding:
                self.isAvoiding = False
                self.avoidCount = 0
            if self.isAvoidingDebris:
                self.isAvoidingDebris = False

            speedLeft = 3.0
            speedRight = 3.0

        elif self.cat_avoid_hold_remaining > 0:
            self.cat_avoid_hold_remaining -= 1
            if self.cat_avoid_hold_remaining <= 0:
                self.isAvoidingCat = False
                speedLeft = 5.0
                speedRight = 5.0
            else:
                self.isAvoidingCat = True
                if self.cat_avoid_direction >= 0:
                    speedLeft = 3.0
                    speedRight = -3.0
                else:
                    speedLeft = -3.0
                    speedRight = 3.0

        elif debris_sum > 5000 or self.isAvoidingDebris:
            if not self.isAvoidingDebris:
                self.isAvoidingDebris = True
                self.debris_avoid_counter = 0
                # Choose turn direction based on which side has less debris
                if debrisL > debrisR:
                    self.debris_avoid_direction = -1  # turn right (away from left debris)
                elif debrisR > debrisL:
                    self.debris_avoid_direction = 1   # turn left (away from right debris)
                # else keep previous direction
                log_event(
                    "DEBUG",
                    logger,
                    event="bot.debris_avoid_started",
                    bot=self.bot.name,
                    mode="avoid_debris",
                    reason="debris_detected",
                    debris_signal=debris_sum,
                )

            if self.debris_avoid_direction >= 0:
                speedLeft = 3.0
                speedRight = -3.0
            else:
                speedLeft = -3.0
                speedRight = 3.0
            self.debris_avoid_counter += 1

            if debris_sum <= 3000:
                log_event(
                    "DEBUG",
                    logger,
                    event="bot.debris_avoid_resolved",
                    bot=self.bot.name,
                    mode=derive_bot_mode(self.bot),
                    reason="debris_cleared",
                )
                self.isAvoidingDebris = False
                self.debris_avoid_counter = 0
                speedLeft = 5.0
                speedRight = 5.0

        elif self.isAvoiding:
            if bot_sum <= 3000:
                log_event(
                    "DEBUG",
                    logger,
                    event="bot.avoid_bot_resolved",
                    bot=self.bot.name,
                    mode=derive_bot_mode(self.bot),
                    reason="bot_signal_cleared",
                )
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
                    log_event(
                        "DEBUG",
                        logger,
                        event="bot.avoid_bot_direction_swapped",
                        bot=self.bot.name,
                        mode="avoid_bot",
                        reason="full_rotation_without_clearance",
                    )
                    self.avoidDirection = -self.avoidDirection
                    self.turn_angle_sum = 0

        elif bot_sum > 3000:
            self.isAvoiding = True
            self.turn_angle_sum = 0

            if random.choice([True, False]):
                self.avoidDirection = 1
                direction = "clockwise"
            else:
                self.avoidDirection = -1
                direction = "counterclockwise"

            log_event(
                "DEBUG",
                logger,
                event="bot.avoid_bot_started",
                bot=self.bot.name,
                mode="avoid_bot",
                reason="bot_detected",
                direction=direction,
                bot_signal=bot_sum,
            )

            if self.avoidDirection == 1:
                speedLeft = 3.0
                speedRight = -3.0
            else:
                speedLeft = -3.0
                speedRight = 3.0

        else:
            if self.currentlyTurning:
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
                reason="cat_signal_reduced" if cat_sum <= self.cat_freeze_threshold else "higher_priority_behavior",
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

        return speedLeft, speedRight, newX, newY
