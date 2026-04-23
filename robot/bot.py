import math
import random
from collections import deque

from app.logging_config import get_logger, log_event
from entities.charger import Charger
from robot import cleaning, motion, sensing
from robot.state_view import derive_bot_mode

logger = get_logger(__name__)


class Bot:
    def __init__(self, namep):
        self.name = namep
        self.x = random.randint(100, 900)
        self.y = random.randint(100, 900)
        self.theta = random.uniform(0.0, 2.0 * math.pi)
        self.ll = 60
        self.sl = 0.0
        self.sr = 0.0
        self.battery = 1000
        self.path = deque()
        self.target_charger = None
        self.astar = None
        self.battery_low_threshold = 600
        self.low_battery_active = False
        self.path_calculated = False
        self.charger = False
        self.actively_charging = False
        self.sensorPositions = [0, 0, 0, 0]
        self._update_sensor_positions()
        self.wait_counter = 0
        self.frame_counter = 0
        self.waiting_for_charger = False
        self.last_logged_mode = None
        self.navigation_turn_bias = 0
        self.replan_cooldown = 0
        self.replan_cooldown_frames = 20
        self.queuing_at_charger = False

    def _update_sensor_positions(self):
        self.sensorPositions = [
            (self.x + 20 * math.sin(self.theta)) + 30 * math.sin((math.pi / 2.0) - self.theta),
            (self.y - 20 * math.cos(self.theta)) + 30 * math.cos((math.pi / 2.0) - self.theta),
            (self.x - 20 * math.sin(self.theta)) + 30 * math.sin((math.pi / 2.0) - self.theta),
            (self.y + 20 * math.cos(self.theta)) + 30 * math.cos((math.pi / 2.0) - self.theta),
        ]

    def setAStar(self, astar):
        self.astar = astar

    def setBrain(self, brainp):
        self.brain = brainp

    def _find_paths_to_chargers(self, chargers, passiveObjects):
        if not chargers:
            return {}

        if hasattr(self.astar, "find_paths_to_targets"):
            targets = []
            for charger in chargers:
                target_x, target_y = charger.getLocation()
                targets.append((charger, target_x, target_y))
            return self.astar.find_paths_to_targets(self.x, self.y, targets, passiveObjects)

        paths = {}
        for charger in chargers:
            target_x, target_y = charger.getLocation()
            paths[charger] = self.astar.find_path(self.x, self.y, target_x, target_y, passiveObjects)
        return paths

    # Queue radius — the zone in which a seeking bot must stop and wait for
    # its turn rather than approach the charger docking area. Previously
    # this was 60 (barely outside the 30-px docking radius), which let
    # followers bump the charging bot. 120 keeps the queue a clear step
    # back from the dock.
    QUEUE_RADIUS = 120
    DOCKING_RADIUS = 30  # mirrors the "at charger" threshold used below

    def _should_queue_at_charger(self, agents):
        """True if the bot should stop and wait rather than approach its target
        charger. Covers three distinct blocking cases:

        1. Logical: another bot is currently charging at this slot.
        2. Approach: another seeker is closer to (or docking at) the same charger.
        3. Physical: another bot is still sitting in the dock area even though
           it is no longer charging — e.g. the bot that just finished charging
           had its logical state reset before it could physically drive away.
        """
        charger = self.target_charger
        if charger is None or not self.charger:
            return False
        if self.battery >= self.battery_low_threshold:
            return False
        my_dist = self.distanceTo(charger)
        if my_dist >= self.QUEUE_RADIUS:
            return False  # not at the queue zone yet

        # Case 1: someone is already charging in our slot.
        if charger.is_charging and charger.charging_bot is not self:
            return True

        # Case 2: another seeker is closer to (or docking at) the same charger.
        # Use target_charger as a soft reservation — ties broken by distance.
        for agent in agents or []:
            if agent is self or not isinstance(agent, Bot):
                continue
            if agent.target_charger is not charger:
                continue
            if getattr(agent, "actively_charging", False):
                return True
            if agent.charger and agent.distanceTo(charger) < my_dist:
                return True

        # Case 3: the dock itself is physically occupied by any bot — covers
        # the window between "charger logically released" and "previous bot
        # has driven clear". Without this, the follower stops queuing the
        # instant reset_charging_state() runs and stalls against the
        # non-penetration layer instead of waiting cleanly.
        dock_block_radius = motion.BOT_CONTACT_DISTANCE
        for agent in agents or []:
            if agent is self or not isinstance(agent, Bot):
                continue
            if agent.distanceTo(charger) < dock_block_radius:
                return True

        return False

    def reset_charging_state(self):
        self.low_battery_active = False
        self.path_calculated = False
        self.path = deque()
        self.target_charger = None
        self.charger = False
        self.actively_charging = False
        self.wait_counter = 0
        self.waiting_for_charger = False
        self.navigation_turn_bias = 0
        self.replan_cooldown = 0
        self.queuing_at_charger = False

    def _log_mode_change(self, reason, **extra_fields):
        new_mode = derive_bot_mode(self)
        if new_mode != self.last_logged_mode:
            log_event(
                "INFO",
                logger,
                event="bot.mode_change",
                bot=self.name,
                from_mode=self.last_logged_mode or "none",
                to_mode=new_mode,
                reason=reason,
                battery=self.battery,
                **extra_fields,
            )
            self.last_logged_mode = new_mode

    def _steer_toward_point(self, target_x, target_y, forward_speed=3.0, turn_speed=2.0):
        dx = motion.wrapped_delta(target_x, self.x)
        dy = motion.wrapped_delta(target_y, self.y)
        target_angle = math.atan2(dy, dx)
        angle_diff = target_angle - self.theta

        if angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        elif angle_diff < -math.pi:
            angle_diff += 2 * math.pi

        if abs(angle_diff) < 0.1:
            self.sl = forward_speed
            self.sr = forward_speed
            self.navigation_turn_bias = 0
            return

        if self.navigation_turn_bias == 0:
            self.navigation_turn_bias = 1 if angle_diff > 0 else -1
        turn_bias = self.navigation_turn_bias

        if turn_bias > 0:
            self.sl = turn_speed
            self.sr = -turn_speed
        else:
            self.sl = -turn_speed
            self.sr = turn_speed

    def thinkAndAct(self, agents, passiveObjects, cats=None):
        if cats is None:
            cats = []
        # Store agents reference for charger allocation in update()
        self._agents_ref = agents

        # Determine queuing state before brain runs so overlap avoidance is
        # suppressed while the bot waits its turn.
        self.queuing_at_charger = self._should_queue_at_charger(agents)

        lightL, lightR = sensing.sense_light(self.sensorPositions, passiveObjects)
        botLightL, botLightR = sensing.sense_other_bots(self.sensorPositions, agents, self)
        debrisL, debrisR = sensing.sense_debris(self.sensorPositions, passiveObjects)
        chargerL, chargerR = sensing.sense_chargers(self.sensorPositions, passiveObjects)
        catL, catR = sensing.sense_cats(self.sensorPositions, cats)

        self.sl, self.sr, xx, yy = self.brain.thinkAndAct(
            lightL,
            lightR,
            chargerL,
            chargerR,
            self.x,
            self.y,
            self.sl,
            self.sr,
            self.battery,
            debrisL,
            debrisR,
            botLightL * 2,
            botLightR * 2,
            catL,
            catR,
        )
        if xx is not None:
            self.x = xx
        if yy is not None:
            self.y = yy

        self._log_mode_change("decision_cycle")

    def update(self, canvas, passiveObjects, dt):
        waiting_for_charger = False
        was_waiting_for_charger = self.waiting_for_charger
        # bot must physically reach the charger (size +/-22) to charge
        near_target_charger = self.target_charger is not None and self.distanceTo(self.target_charger) < 30

        if self.charger and self.battery < self.battery_low_threshold:
            charger_occupied_by_other = (
                self.target_charger is not None
                and self.target_charger.is_charging
                and self.target_charger.charging_bot is not self
            )
            if charger_occupied_by_other and (near_target_charger or self.queuing_at_charger):
                waiting_for_charger = True

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

        if self.battery < self.battery_low_threshold:
            if not self.low_battery_active:
                self.low_battery_active = True
                self.charger = True
                log_event(
                    "INFO",
                    logger,
                    event="bot.low_battery_entered",
                    bot=self.name,
                    mode=derive_bot_mode(self),
                    reason="battery_below_threshold",
                    battery=self.battery,
                )

            # Count how many other bots are already targeting each charger.
            other_agents = getattr(self, "_agents_ref", []) or []

            def _competitors(charger):
                count = 0
                for agent in other_agents:
                    if agent is self:
                        continue
                    if isinstance(agent, Bot) and getattr(agent, "target_charger", None) is charger:
                        count += 1
                return count

            available_chargers = []
            occupied_chargers = []
            all_chargers = []
            for obj in passiveObjects:
                if not isinstance(obj, Charger):
                    continue

                all_chargers.append(obj)
                distance = self.distanceTo(obj)
                rivals = _competitors(obj)
                if not obj.is_charging or obj.charging_bot == self:
                    available_chargers.append((rivals, distance, obj))
                else:
                    occupied_chargers.append((rivals, distance, obj))

            if self.replan_cooldown > 0:
                self.replan_cooldown -= 1

            should_probe_candidate_paths = bool(all_chargers) and (
                not self.path_calculated
                or (self.path_calculated and not self.path and not near_target_charger and self.replan_cooldown <= 0)
                or (self.target_charger is not None and not near_target_charger)
            )
            charger_paths = (
                self._find_paths_to_chargers(all_chargers, passiveObjects)
                if should_probe_candidate_paths
                else {}
            )

            reachable_available_alternative_exists = False
            closer_reachable_available_charger_exists = False
            if self.target_charger is not None and not near_target_charger:
                current_target_path = charger_paths.get(self.target_charger)
                current_target_cost = len(current_target_path) if current_target_path else float('inf')
                for _, _, obj in available_chargers:
                    if obj is self.target_charger:
                        continue
                    alt_path = charger_paths.get(obj)
                    if not alt_path:
                        continue

                    reachable_available_alternative_exists = True
                    if len(alt_path) < current_target_cost:
                        closer_reachable_available_charger_exists = True
                        break

            target_blocked_while_far = (
                self.target_charger is not None
                and self.target_charger.is_charging
                and self.target_charger.charging_bot != self
                and not near_target_charger
                and not self.queuing_at_charger
                and reachable_available_alternative_exists
            )

            should_recalculate_path = (
                not self.path_calculated
                or (self.path_calculated and not self.path and not near_target_charger
                    and self.replan_cooldown <= 0)
                or target_blocked_while_far
                or closer_reachable_available_charger_exists
            )

            if should_recalculate_path:
                if not self.path_calculated:
                    replan_reason = "low_battery_initial"
                elif self.path_calculated and not self.path and not near_target_charger:
                    replan_reason = "path_exhausted"
                elif target_blocked_while_far:
                    replan_reason = "target_blocked"
                else:
                    replan_reason = "closer_target_available"

                log_event(
                    "INFO",
                    logger,
                    event="bot.replan_started",
                    bot=self.name,
                    mode=derive_bot_mode(self),
                    reason=replan_reason,
                    battery=self.battery,
                    current_target=self.target_charger.name if self.target_charger else None,
                )

                selected_charger = None
                selected_path = None

                def _path_cost(item):
                    path = charger_paths.get(item[2])
                    return (item[0], len(path) if path else float('inf'))

                for charger_candidates in (
                    sorted(available_chargers, key=_path_cost),
                    sorted(occupied_chargers, key=_path_cost),
                ):
                    for _, _, candidate in charger_candidates:
                        path = charger_paths.get(candidate)
                        if path:
                            selected_charger = candidate
                            selected_path = path
                            break
                    if selected_path:
                        break

                self.path_calculated = True
                if selected_charger and selected_path:
                    self.target_charger = selected_charger
                    self.path = selected_path
                    self.navigation_turn_bias = 0
                    self.charger = True
                    log_event(
                        "INFO",
                        logger,
                        event="bot.replan_selected",
                        bot=self.name,
                        mode=derive_bot_mode(self),
                        reason=replan_reason,
                        battery=self.battery,
                        new_target=selected_charger.name,
                        path_len=len(selected_path),
                    )
                else:
                    log_event(
                        "WARNING",
                        logger,
                        event="bot.path_not_found",
                        bot=self.name,
                        mode=derive_bot_mode(self),
                        reason=replan_reason,
                        battery=self.battery,
                        current_target=self.target_charger.name if self.target_charger else None,
                    )
                    self.target_charger = None
                    self.path = deque()
                    self.replan_cooldown = self.replan_cooldown_frames
        elif not self.charger and self.low_battery_active:
            self.reset_charging_state()

        # must walk onto the charger (distance < 30) to charge, no wireless
        nearby_chargers = [obj for obj in passiveObjects if isinstance(obj, Charger) and self.distanceTo(obj) < 30]
        available_nearby = [obj for obj in nearby_chargers if not obj.is_charging or obj.charging_bot == self]

        selected_charger = None
        engaged_with_charger = False
        if self.target_charger in available_nearby:
            selected_charger = self.target_charger
        elif available_nearby:
            selected_charger = min(available_nearby, key=self.distanceTo)
            self.target_charger = selected_charger
            self.path = deque()
        elif self.target_charger in nearby_chargers:
            selected_charger = self.target_charger

        self.waiting_for_charger = bool(
            selected_charger
            and self.charger
            and selected_charger.is_charging
            and selected_charger.charging_bot != self
        )
        if self.waiting_for_charger and not was_waiting_for_charger:
            log_event(
                "INFO",
                logger,
                event="bot.waiting_for_charger",
                bot=self.name,
                mode="waiting_for_charger",
                reason="charger_busy",
                battery=self.battery,
                charger=selected_charger.name if selected_charger else None,
            )
        elif was_waiting_for_charger and not self.waiting_for_charger:
            log_event(
                "INFO",
                logger,
                event="bot.waiting_for_charger_resolved",
                bot=self.name,
                mode=derive_bot_mode(self),
                reason="charger_available",
                battery=self.battery,
                charger=selected_charger.name if selected_charger else None,
            )

        for obj in passiveObjects:
            if isinstance(obj, Charger) and obj.charging_bot == self and obj is not selected_charger:
                obj.stop_charging()

        # Not near any charger -> not actively charging
        if not selected_charger:
            self.actively_charging = False

        if selected_charger and self.charger and self.battery < 1000:
            if selected_charger.is_charging and selected_charger.charging_bot != self:
                self.sl = 0.0
                self.sr = 0.0
                self.actively_charging = False
                engaged_with_charger = True
            else:
                if not selected_charger.is_charging:
                    if selected_charger.start_charging(self):
                        log_event(
                            "INFO",
                            logger,
                            event="bot.charging_started",
                            bot=self.name,
                            mode="charging",
                            reason="charger_reached",
                            battery=self.battery,
                            charger=selected_charger.name,
                        )

                self.actively_charging = True
                self.battery = min(self.battery + 10, 1000)
                self.sl = 0.0
                self.sr = 0.0
                self.path = deque()
                engaged_with_charger = True

                if self.battery >= 1000:
                    selected_charger.stop_charging()
                    completed_charger = selected_charger.name
                    self.reset_charging_state()
                    log_event(
                        "INFO",
                        logger,
                        event="bot.charging_completed",
                        bot=self.name,
                        mode=derive_bot_mode(self),
                        reason="battery_full",
                        battery=self.battery,
                        charger=completed_charger,
                    )

        if engaged_with_charger:
            self._log_mode_change("charging_state_update")
            self.move(canvas, dt)
            return

        if self.battery <= 0:
            self.sl = 0.0
            self.sr = 0.0
            self._log_mode_change("battery_depleted")
            self.move(canvas, dt)
            return

        if self.charger and self.battery < self.battery_low_threshold:
            # Queuing: bot is close to its target charger but another bot is
            # charging there.  Stop and wait in place instead of fighting with
            # overlap avoidance (which caused the "bumping" effect).
            if self.queuing_at_charger:
                self.sl = 0.0
                self.sr = 0.0
                log_event(
                    "DEBUG",
                    logger,
                    event="bot.queuing_at_charger",
                    bot=self.name,
                    mode="queuing",
                    reason="charger_busy_nearby",
                    battery=self.battery,
                    charger=self.target_charger.name if self.target_charger else None,
                )
                self._log_mode_change("queuing_at_charger")
                self.move(canvas, dt)
                return

            if hasattr(self, "brain") and self.brain.isOverlapping:
                self._log_mode_change("overlap_separation")
                self.move(canvas, dt)
                return

            if self.path:
                while self.path:
                    target_x, target_y = self.path[0]
                    dx = target_x - self.x
                    dy = target_y - self.y
                    distance = math.sqrt(dx * dx + dy * dy)

                    if distance < 20:
                        self.navigation_turn_bias = 0
                        self.path.popleft()
                        if not self.path:
                            log_event(
                                "DEBUG",
                                logger,
                                event="bot.path_following_completed",
                                bot=self.name,
                                mode=derive_bot_mode(self),
                                reason="charger_nearby",
                                target=self.target_charger.name if self.target_charger else None,
                            )
                        continue

                    self._steer_toward_point(target_x, target_y)
                    self.brain.isAvoiding = False
                    break

            # No path but have target charger -- move directly toward it
            elif self.target_charger is not None and not near_target_charger:
                cx, cy = self.target_charger.getLocation()
                self._steer_toward_point(cx, cy)
                self.brain.isAvoiding = False

        self._log_mode_change("movement_update")
        self.move(canvas, dt)

    def draw(self, canvas):
        from ui.renderer import (
            draw_bot_battery_bar,
            draw_bot_direction_arrow,
            draw_bot_path,
            draw_bot_status_label,
        )
        from ui.theme import BOT_COLOR_AVOIDING, BOT_COLOR_CHARGING, BOT_COLOR_DEPLETED, BOT_COLOR_NORMAL, BOT_BODY_COLOR

        if self.battery <= 0:
            body_color = BOT_COLOR_DEPLETED
        elif hasattr(self, "brain") and self.brain.isAvoiding:
            body_color = BOT_COLOR_AVOIDING
        elif self.actively_charging:
            body_color = BOT_COLOR_CHARGING
        else:
            body_color = BOT_COLOR_NORMAL

        # Circular robot vacuum body
        bot_radius = 28
        canvas.create_oval(
            self.x - bot_radius, self.y - bot_radius,
            self.x + bot_radius, self.y + bot_radius,
            fill=body_color, outline="#333344", width=2, tags=self.name,
        )

        self._update_sensor_positions()

        # Inner gold disc (centered on bot)
        canvas.create_oval(self.x - 14, self.y - 14, self.x + 14, self.y + 14, fill=BOT_BODY_COLOR, outline="#b09020", width=1, tags=self.name)
        canvas.create_text(self.x, self.y, text=str(self.battery), fill="#1e1e2e", font=("Helvetica", 9, "bold"), tags=self.name)

        wheel1PosX = self.x - 30 * math.sin(self.theta)
        wheel1PosY = self.y + 30 * math.cos(self.theta)
        canvas.create_oval(wheel1PosX - 4, wheel1PosY - 4, wheel1PosX + 4, wheel1PosY + 4, fill="#cc4444", outline="#992222", tags=self.name)

        wheel2PosX = self.x + 30 * math.sin(self.theta)
        wheel2PosY = self.y - 30 * math.cos(self.theta)
        canvas.create_oval(wheel2PosX - 4, wheel2PosY - 4, wheel2PosX + 4, wheel2PosY + 4, fill="#44cc44", outline="#229922", tags=self.name)

        # Draw sensor dots at the front edge of the circular body
        fwd_dist = 28
        side_dist = 10
        cos_t, sin_t = math.cos(self.theta), math.sin(self.theta)
        s1x = self.x + cos_t * fwd_dist + sin_t * side_dist
        s1y = self.y + sin_t * fwd_dist - cos_t * side_dist
        s2x = self.x + cos_t * fwd_dist - sin_t * side_dist
        s2y = self.y + sin_t * fwd_dist + cos_t * side_dist
        canvas.create_oval(s1x - 3, s1y - 3, s1x + 3, s1y + 3, fill="#f0d060", outline="#c0a030", tags=self.name)
        canvas.create_oval(s2x - 3, s2y - 3, s2x + 3, s2y + 3, fill="#f0d060", outline="#c0a030", tags=self.name)

        # Enhanced visualizations
        draw_bot_path(canvas, self)
        draw_bot_direction_arrow(canvas, self)
        draw_bot_battery_bar(canvas, self)
        draw_bot_status_label(canvas, self)

    def move(self, canvas, dt):
        motion.advance(self, dt)
        motion.wrap(self)
        # Hard non-penetration floor: sensor-based overlap recovery can't
        # react fast enough to stop two bots from entering each other's
        # body radius, so clamp the position after advance() against every
        # other bot. The engine runs agents serially, so the cached
        # `_agents_ref` reflects everyone's up-to-date position this frame.
        other_bots = [
            agent for agent in getattr(self, "_agents_ref", []) or []
            if agent is not self and isinstance(agent, Bot)
        ]
        if other_bots:
            motion.resolve_bot_collisions(self, other_bots)
        canvas.delete(self.name)
        self.draw(canvas)

    def distanceTo(self, obj):
        return motion.distance_to(self, obj)

    def collectDirt(self, canvas, passiveObjects, count, debris_count, current_time=None):
        return cleaning.collect_dirt(self, canvas, passiveObjects, count, debris_count, current_time=current_time)
