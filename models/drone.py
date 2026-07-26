"""
Autonomous Drone Model with AI Finite State Machine (FSM), Vector Steering, and Battery Management.
"""

import math
import random
import heapq
from config import (
    DRONE_MAX_SPEED, DRONE_CRUISE_SPEED, DRONE_ACCELERATION, DRONE_TURN_RATE,
    DRONE_BATTERY_DRAIN_NORMAL, DRONE_BATTERY_DRAIN_THERMAL, DRONE_BATTERY_RTB_THRESHOLD,
    DRONE_BATTERY_RECHARGE_RATE, COLOR_ACCENT_BLUE
)
from models.sensors import RaycastSensor, ThermalImagingCamera, AIFireClassifier
from utils.geo import pixel_to_gps, format_gps, distance_pixels

class DroneState:
    PATROL = "PATROL"
    INVESTIGATE = "INVESTIGATE"
    AVOID_OBSTACLE = "AVOID_OBSTACLE"
    RETURN_TO_BASE = "RETURN_TO_BASE"
    CHARGING = "CHARGING"
    ANALYZE = "ANALYZE"


class AutonomousDrone:
    """Autonomous Patrol Drone carrying thermal imaging sensor payload and AI agent state machine."""
    def __init__(self, drone_id: str, start_pos: tuple[float, float], waypoints: list[tuple[float, float]], color=COLOR_ACCENT_BLUE):
        self.drone_id = drone_id
        self.x, self.y = start_pos
        self.vx = 0.0
        self.vy = 0.0
        self.heading = random.uniform(0, 2 * math.pi)
        self.speed = DRONE_CRUISE_SPEED
        self.color = color

        # Waypoint Patrol System
        self.waypoints = waypoints
        self.current_wp_index = 0
        
        # AI State Machine
        self.state = DroneState.PATROL
        self.target_pos = self.waypoints[0] if waypoints else start_pos
        self.manual_recall = False
        self.analysis_progress = 0.0
        
        # Battery Parameters
        self.battery = random.uniform(88.0, 100.0) # Initial charge
        self.is_low_battery = False

        # Sensor Payload & AI Classifier
        self.raycast = RaycastSensor()
        self.thermal_cam = ThermalImagingCamera()
        self.ai_classifier = AIFireClassifier()

        # Telemetry State
        self.last_thermal_scan = {'peak_temp': 25.0, 'avg_temp': 25.0, 'std_temp': 0.0, 'hotspot_pos': None}
        self.smoothed_peak_temp = 25.0
        self.smoothed_avg_temp = 25.0
        self.smoothed_std_temp = 0.0
        self.rtb_path = []
        self.current_rtb_index = 0
        self.detected_fires_count = 0

    @property
    def position(self) -> tuple[float, float]:
        return (self.x, self.y)

    @property
    def gps_coordinates(self) -> tuple[float, float]:
        return pixel_to_gps(self.x, self.y)

    @property
    def gps_string(self) -> str:
        lat, lon = self.gps_coordinates
        return format_gps(lat, lon)

    def update(self, env) -> dict | None:
        """
        Main update loop executed per frame. Handles state transition, vector steering, obstacle avoidance, battery drain, and thermal AI scanning.
        Returns alert payload if AI detects fire, else None.
        """
        alert_payload = None

        # 1. Update Battery Status
        self._update_battery(env)

        # 2. State Machine AI Logic
        if self.state == DroneState.CHARGING:
            self._handle_charging_state(env)
            return None

        # Check battery trigger for Autonomous Return-To-Base (RTB)
        if self.battery <= DRONE_BATTERY_RTB_THRESHOLD and self.state != DroneState.RETURN_TO_BASE:
            self.state = DroneState.RETURN_TO_BASE
            self.rtb_path = self._find_path_astar(self.position, env.base_station, env)
            self.current_rtb_index = 0
            if self.rtb_path:
                self.target_pos = self.rtb_path[0]
            else:
                self.target_pos = env.base_station

        # Execute current state behavior
        if self.state == DroneState.PATROL:
            self._handle_patrol_state(env)
        elif self.state == DroneState.INVESTIGATE:
            self._handle_investigate_state(env)
        elif self.state == DroneState.ANALYZE:
            self._handle_analyze_state(env)
        elif self.state == DroneState.RETURN_TO_BASE:
            self._handle_rtb_state(env)

        # 3. Vector Steering & Physics Movement
        self._apply_steering(env)

        # 4. Perform Thermal Camera AI Scanning (if not charging)
        self.last_thermal_scan = self.thermal_cam.sample_thermal_region(self.position, env)
        
        # Apply EMA smoothing to thermal metrics
        alpha = 0.15
        self.smoothed_peak_temp += alpha * (self.last_thermal_scan['peak_temp'] - self.smoothed_peak_temp)
        self.smoothed_avg_temp += alpha * (self.last_thermal_scan['avg_temp'] - self.smoothed_avg_temp)
        self.smoothed_std_temp += alpha * (self.last_thermal_scan['std_temp'] - self.smoothed_std_temp)
        
        # Check for thermal plume or heat anomaly in sector
        nearest_fire = None
        min_d = 999999.0
        for fire in env.fires:
            if fire.active and not fire.alert_sent:
                d = distance_pixels(self.position, (fire.x, fire.y))
                if d < min_d:
                    min_d = d
                    nearest_fire = fire

        # Vector towards nearest anomaly if within long-range sensor detection radius (420px)
        if nearest_fire and min_d < 420.0 and self.state == DroneState.PATROL:
            self.state = DroneState.INVESTIGATE
            self.target_pos = (nearest_fire.x, nearest_fire.y)

        # AI Classifier Evaluation (runs only when close analysis is completed)
        if self.state == DroneState.ANALYZE and self.analysis_progress >= 100.0:
            alert = self.ai_classifier.classify_hotspot(self.drone_id, self.position, self.last_thermal_scan)
            if alert and alert['classification'] in ("POTENTIAL_FIRE", "CONFIRMED_WILDFIRE"):
                alert_payload = alert
                
            # Transition back to patrol state after completing analysis
            self.state = DroneState.PATROL
            self.analysis_progress = 0.0

        return alert_payload

    def _update_battery(self, env):
        """Simulates battery depletion during flight and recharging at base."""
        if self.state == DroneState.CHARGING:
            self.battery = min(100.0, self.battery + DRONE_BATTERY_RECHARGE_RATE)
        else:
            drain = DRONE_BATTERY_DRAIN_THERMAL if self.state in (DroneState.INVESTIGATE, DroneState.ANALYZE) else DRONE_BATTERY_DRAIN_NORMAL
            self.battery = max(0.0, self.battery - drain)

    def _handle_patrol_state(self, env):
        """Patrols sequence of waypoints smoothly."""
        if not self.waypoints:
            return

        self.target_pos = self.waypoints[self.current_wp_index]
        dist = distance_pixels(self.position, self.target_pos)

        # Reach waypoint check
        if dist < 30.0:
            self.current_wp_index = (self.current_wp_index + 1) % len(self.waypoints)
            self.target_pos = self.waypoints[self.current_wp_index]

    def _handle_investigate_state(self, env):
        """Investigates a detected hotspot for close inspection."""
        dist = distance_pixels(self.position, self.target_pos)
        
        # Check if the target fire is still active
        target_active = False
        for fire in env.fires:
            if fire.active and distance_pixels((fire.x, fire.y), self.target_pos) < 10.0:
                target_active = True
                break
                
        if not target_active:
            # Fire went inactive or was closed
            self.state = DroneState.PATROL
            return

        # Start close analysis if we are close enough
        if dist < 40.0:
            self.state = DroneState.ANALYZE
            self.analysis_progress = 0.0

    def _handle_analyze_state(self, env):
        """Hover over target hotspot and perform detailed multi-sensor AI analysis."""
        # Check if the target fire is still active
        target_active = False
        for fire in env.fires:
            if fire.active and distance_pixels((fire.x, fire.y), self.target_pos) < 10.0:
                target_active = True
                break
                
        if not target_active:
            self.state = DroneState.PATROL
            self.analysis_progress = 0.0
            return

        # Increment progress. 2.5 per frame at 60 FPS means it takes 40 frames (~0.67 seconds)
        self.analysis_progress = min(100.0, self.analysis_progress + 2.5)

    def recall_to_base(self, env):
        """Commands drone to abort current mission and return to base station dock using A* path."""
        self.state = DroneState.RETURN_TO_BASE
        self.manual_recall = True
        self.rtb_path = self._find_path_astar(self.position, env.base_station, env)
        self.current_rtb_index = 0
        if self.rtb_path:
            self.target_pos = self.rtb_path[0]
        else:
            self.target_pos = env.base_station

    def resume_patrol(self):
        """Resumes patrol flight path from docking station."""
        self.manual_recall = False
        self.state = DroneState.PATROL
        self.rtb_path = []
        if self.waypoints:
            self.target_pos = self.waypoints[self.current_wp_index]

    def _handle_rtb_state(self, env):
        """Navigates back to docking station using computed A* path."""
        if not self.rtb_path:
            self.target_pos = env.base_station
            dist = distance_pixels(self.position, self.target_pos)
            if dist < 25.0:
                self.state = DroneState.CHARGING
            return

        self.target_pos = self.rtb_path[self.current_rtb_index]
        dist = distance_pixels(self.position, self.target_pos)
        if dist < 30.0:
            self.current_rtb_index += 1
            if self.current_rtb_index >= len(self.rtb_path):
                self.state = DroneState.CHARGING
                self.rtb_path = []
            else:
                self.target_pos = self.rtb_path[self.current_rtb_index]

    def _find_path_astar(self, start: tuple[float, float], goal: tuple[float, float], env) -> list[tuple[float, float]]:
        """Computes obstacle-aware path from start to goal using A* algorithm on a downsampled grid."""
        cell_size = 20
        cols = env.width // cell_size
        rows = env.height // cell_size
        
        start_cell = (int(start[0] // cell_size), int(start[1] // cell_size))
        goal_cell = (int(goal[0] // cell_size), int(goal[1] // cell_size))
        
        # Clamp within grid bounds
        start_cell = (max(0, min(cols - 1, start_cell[0])), max(0, min(rows - 1, start_cell[1])))
        goal_cell = (max(0, min(cols - 1, goal_cell[0])), max(0, min(rows - 1, goal_cell[1])))
        
        def get_cell_cost(c):
            cx = c[0] * cell_size + cell_size / 2
            cy = c[1] * cell_size + cell_size / 2
            # Hard obstacle base + buffer cost
            if env.is_obstacle(cx, cy, margin=20):
                return 1000.0  # Avoid completely if possible
            if env.is_obstacle(cx, cy, margin=35):
                return 8.0     # Prefer path with more clearance
            return 1.0
            
        queue = []
        heapq.heappush(queue, (0, 0, start_cell, [start_cell]))
        visited = set()
        
        while queue:
            f, g, curr, path = heapq.heappop(queue)
            
            if curr == goal_cell:
                pixel_path = []
                for c in path:
                    pixel_path.append((c[0] * cell_size + cell_size / 2, c[1] * cell_size + cell_size / 2))
                pixel_path.append(goal)
                return pixel_path
                
            if curr in visited:
                continue
            visited.add(curr)
            
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
                neighbor = (curr[0] + dx, curr[1] + dy)
                if 0 <= neighbor[0] < cols and 0 <= neighbor[1] < rows:
                    cost_multiplier = get_cell_cost(neighbor)
                    base_cost = 1.414 if (dx != 0 and dy != 0) else 1.0
                    step_cost = base_cost * cost_multiplier
                    new_g = g + step_cost
                    h = math.hypot(neighbor[0] - goal_cell[0], neighbor[1] - goal_cell[1])
                    new_f = new_g + h
                    heapq.heappush(queue, (new_f, new_g, neighbor, path + [neighbor]))
                    
        return [start, goal]

    def _handle_charging_state(self, env):
        """Docks at station until battery reaches 100%."""
        self.x, self.y = env.base_station
        self.vx = 0.0
        self.vy = 0.0
        
        # Charge battery
        if self.battery < 100.0:
            self.battery = min(100.0, self.battery + DRONE_BATTERY_RECHARGE_RATE)

        # Resume patrol automatically once battery is fully charged (>= 99.5)
        if self.battery >= 99.5:
            self.battery = 100.0
            self.manual_recall = False
            self.state = DroneState.PATROL
            self.rtb_path = []
            if self.waypoints:
                self.target_pos = self.waypoints[self.current_wp_index]

    def _apply_steering(self, env):
        """
        Applies target attraction force + raycast obstacle repulsion force.
        Ensures smooth turning physics and hill avoidance.
        """
        # 1. Target Attraction Force
        dx = self.target_pos[0] - self.x
        dy = self.target_pos[1] - self.y
        desired_angle = math.atan2(dy, dx)

        # 2. Obstacle Repulsion Force (Raycasting)
        ray_results = self.raycast.scan(self.position, self.heading, env)
        repulsion_x = 0.0
        repulsion_y = 0.0

        for angle, dist in ray_results:
            if dist < 70.0: # Danger zone
                weight = (70.0 - dist) / 70.0
                repulsion_x -= math.cos(angle) * weight * 2.5
                repulsion_y -= math.sin(angle) * weight * 2.5

        # Combine desired angle with obstacle avoidance angle
        if math.hypot(repulsion_x, repulsion_y) > 0.1:
            rep_len = math.hypot(repulsion_x, repulsion_y)
            nx = repulsion_x / rep_len
            ny = repulsion_y / rep_len
            
            # Perpendicular tangents
            tx1, ty1 = -ny, nx
            tx2, ty2 = ny, -nx
            
            # Desired movement vector
            dx_des = math.cos(desired_angle)
            dy_des = math.sin(desired_angle)
            
            # Choose tangent closest to desired direction
            dot1 = tx1 * dx_des + ty1 * dy_des
            dot2 = tx2 * dx_des + ty2 * dy_des
            
            if dot1 > dot2:
                tx, ty = tx1, ty1
            else:
                tx, ty = tx2, ty2
                
            # Add tangent slide component to the repulsion force
            slide_weight = 1.5
            avoid_x = repulsion_x + tx * rep_len * slide_weight
            avoid_y = repulsion_y + ty * rep_len * slide_weight
            
            avoid_angle = math.atan2(avoid_y, avoid_x)
            target_angle = 0.4 * desired_angle + 0.6 * avoid_angle
        else:
            target_angle = desired_angle

        # Smooth Heading Turn (Angular Velocity limit)
        angle_diff = (target_angle - self.heading + math.pi) % (2 * math.pi) - math.pi
        self.heading += max(-DRONE_TURN_RATE, min(DRONE_TURN_RATE, angle_diff))

        # Velocity Update (hover if analyzing)
        current_speed = 0.0 if self.state == DroneState.ANALYZE else self.speed
        target_vx = math.cos(self.heading) * current_speed
        target_vy = math.sin(self.heading) * current_speed

        self.vx += (target_vx - self.vx) * DRONE_ACCELERATION
        self.vy += (target_vy - self.vy) * DRONE_ACCELERATION

        # Update position with map boundary clamping
        self.x = max(15.0, min(env.width - 15.0, self.x + self.vx))
        self.y = max(15.0, min(env.height - 15.0, self.y + self.vy))
