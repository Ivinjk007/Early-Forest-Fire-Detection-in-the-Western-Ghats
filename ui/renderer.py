"""
Simulation Viewport Renderer.
Renders Western Ghats forest terrain, hills, river streams, dynamic heat particle effects, drone quadcopters, thermal FOVs, and raycasts.
"""

import math
import pygame
import numpy as np
from config import (
    MAP_WIDTH, MAP_HEIGHT, COLOR_FOREST_CANOPY, COLOR_WATER,
    COLOR_HILL_BASE, COLOR_HILL_PEAK, COLOR_BASE_DOCK, COLOR_ACCENT_RED,
    COLOR_ACCENT_AMBER, COLOR_ACCENT_GREEN, COLOR_TEXT_PRIMARY, COLOR_BG_DARK,
    THERMAL_FOV_RADIUS
)
from models.drone import DroneState

class EnvironmentRenderer:
    """Handles high-performance Pygame rendering of map viewport and simulation entities."""
    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self.font_sm = pygame.font.SysFont("Segoe UI", 12)
        self.font_bold = pygame.font.SysFont("Segoe UI", 13, bold=True)
        
        # Pre-render background surface for terrain performance
        self.bg_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT))
        self._render_static_terrain()

    def _render_static_terrain(self):
        """Draws static forest layer, river, elevation hills, and base station."""
        # Forest Base
        self.bg_surface.fill(COLOR_FOREST_CANOPY)

        # Draw River Stream
        river_points = [
            (0, 300), (150, 320), (300, 280), (450, 350), 
            (600, 330), (750, 410), (MAP_WIDTH, 390)
        ]
        pygame.draw.lines(self.bg_surface, COLOR_WATER, False, river_points, 18)
        pygame.draw.lines(self.bg_surface, (50, 110, 160), False, river_points, 6)

        # Draw Hill Obstacles (Concentric rings for 3D topo elevation feel)
        hills_data = [
            (240, 200, 75, "Hill 1400m"),
            (580, 160, 90, "Ridge 1800m"),
            (750, 480, 110, "Peak 2100m"),
            (360, 520, 85, "Hill 1650m"),
            (160, 420, 65, "Hill 1200m"),
            (520, 680, 70, "Ridge 1350m")
        ]

        for hx, hy, hr, label in hills_data:
            # Outer base ring
            pygame.draw.circle(self.bg_surface, COLOR_HILL_BASE, (hx, hy), hr)
            # Inner elevation rings
            for step in range(1, 4):
                r = hr * (1.0 - step * 0.22)
                col_factor = step / 4.0
                r_c = int(COLOR_HILL_BASE[0] + col_factor * (COLOR_HILL_PEAK[0] - COLOR_HILL_BASE[0]))
                g_c = int(COLOR_HILL_BASE[1] + col_factor * (COLOR_HILL_PEAK[1] - COLOR_HILL_BASE[1]))
                b_c = int(COLOR_HILL_BASE[2] + col_factor * (COLOR_HILL_PEAK[2] - COLOR_HILL_BASE[2]))
                pygame.draw.circle(self.bg_surface, (r_c, g_c, b_c), (hx, hy), int(r))

            # Hill label
            lbl = self.font_sm.render(label, True, (160, 185, 170))
            self.bg_surface.blit(lbl, (hx - lbl.get_width()//2, hy - 6))

        # Base Station Docking Pad
        base_x, base_y = 90, MAP_HEIGHT - 90
        pygame.draw.circle(self.bg_surface, (20, 80, 45), (base_x, base_y), 32)
        pygame.draw.circle(self.bg_surface, COLOR_BASE_DOCK, (base_x, base_y), 32, 2)
        pygame.draw.circle(self.bg_surface, COLOR_BASE_DOCK, (base_x, base_y), 8)
        
        lbl_dock = self.font_bold.render("BASE DOCK", True, COLOR_BASE_DOCK)
        self.bg_surface.blit(lbl_dock, (base_x - lbl_dock.get_width()//2, base_y + 36))

    def render(self, env, drones: list, show_thermal_overlay: bool = True, show_raycast: bool = True):
        """Main rendering pass."""
        # 1. Blit Static Terrain Background
        self.surface.blit(self.bg_surface, (0, 0))

        # 2. Render Thermal Heat Overlay & FOV Circles
        if show_thermal_overlay:
            self._render_thermal_fovs(drones, env)

        # 3. Render Fires & Smoke Particles
        self._render_fires_and_particles(env)

        # 4. Render Drone Waypoint Paths & Raycasts
        for drone in drones:
            if show_raycast:
                self._render_drone_raycast(drone, env)
            self._render_waypoint_path(drone)

        # 5. Render Drone Models & Telemetry Badges
        for drone in drones:
            self._render_drone(drone)

        # 6. Render Alert Pins
        self._render_alert_pins(env)

    def _render_thermal_fovs(self, drones: list, env):
        """Draws semi-transparent thermal FOV scanning cones underneath drones."""
        fov_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT), pygame.SRCALPHA)
        
        for drone in drones:
            if drone.state == DroneState.CHARGING:
                continue

            px, py = int(drone.x), int(drone.y)
            peak_temp = drone.last_thermal_scan['peak_temp']

            # Color changes based on thermal detection intensity
            if peak_temp >= 200.0:
                fov_color = (248, 113, 113, 85) # Red highlight for wildfire
            elif peak_temp >= 50.0:
                fov_color = (251, 191, 36, 75)  # Amber highlight for hotspot
            else:
                fov_color = (56, 189, 248, 45)  # Normal sky blue FOV

            # Outer FOV circle
            pygame.draw.circle(fov_surface, fov_color, (px, py), int(THERMAL_FOV_RADIUS))
            pygame.draw.circle(fov_surface, (fov_color[0], fov_color[1], fov_color[2], 160), (px, py), int(THERMAL_FOV_RADIUS), 1)

            # Scanner Radar line sweep animation
            sweep_angle = (pygame.time.get_ticks() * 0.003) % (2 * math.pi)
            rx = px + math.cos(sweep_angle) * THERMAL_FOV_RADIUS
            ry = py + math.sin(sweep_angle) * THERMAL_FOV_RADIUS
            pygame.draw.line(fov_surface, (255, 255, 255, 140), (px, py), (rx, ry), 1)

        self.surface.blit(fov_surface, (0, 0))

    def _render_fires_and_particles(self, env):
        """Renders smoke particles and animated fire cores."""
        # Smoke and fire particles
        particle_surf = pygame.Surface((MAP_WIDTH, MAP_HEIGHT), pygame.SRCALPHA)
        for p in env.particles:
            alpha = max(0, min(255, int(p['alpha'])))
            if p['type'] == 'smoke':
                col = (140, 150, 160, alpha // 2)
            else:
                col = (255, 140, 30, alpha)
            pygame.draw.circle(particle_surf, col, (int(p['x']), int(p['y'])), int(p['radius']))

        self.surface.blit(particle_surf, (0, 0))

        # Active & Closed Fire Hotspots
        for fire in env.fires:
            fx, fy = int(fire.x), int(fire.y)
            if not fire.active:
                # Render closed/extinguished fire representation
                pygame.draw.circle(self.surface, (34, 197, 94), (fx, fy), 10, 2)
                pygame.draw.line(self.surface, (34, 197, 94), (fx - 6, fy - 6), (fx + 6, fy + 6), 2)
                pygame.draw.line(self.surface, (34, 197, 94), (fx + 6, fy - 6), (fx - 6, fy + 6), 2)
                
                c_lbl = self.font_sm.render("CLOSED", True, (34, 197, 94))
                self.surface.blit(c_lbl, (fx - c_lbl.get_width()//2, fy - 22))
                continue
            
            # Pulsing heat glow ring
            pulse = math.sin(pygame.time.get_ticks() * 0.01) * 4.0
            r_glow = max(10, int(fire.radius + pulse))
            
            glow_surf = pygame.Surface((r_glow*2, r_glow*2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (248, 113, 113, 90), (r_glow, r_glow), r_glow)
            self.surface.blit(glow_surf, (fx - r_glow, fy - r_glow))

            # Fire core
            pygame.draw.circle(self.surface, (239, 68, 68), (fx, fy), 12)
            pygame.draw.circle(self.surface, (251, 191, 36), (fx, fy), 7)
            pygame.draw.circle(self.surface, (255, 255, 255), (fx, fy), 3)

            # Temp label
            t_lbl = self.font_bold.render(f"{int(fire.temp_c)}°C", True, COLOR_TEXT_PRIMARY)
            self.surface.blit(t_lbl, (fx - t_lbl.get_width()//2, fy - 26))

    def _render_drone_raycast(self, drone, env):
        """Draws raycast obstacle sensor distance lines."""
        if drone.state == DroneState.CHARGING:
            return
        
        ray_results = drone.raycast.scan(drone.position, drone.heading, env)
        ray_surf = pygame.Surface((MAP_WIDTH, MAP_HEIGHT), pygame.SRCALPHA)
        
        for angle, dist in ray_results:
            rx = drone.x + math.cos(angle) * dist
            ry = drone.y + math.sin(angle) * dist
            
            # Highlight rays detecting hill obstacle in red
            if dist < 65.0:
                col = (248, 113, 113, 180) # Danger ray
            else:
                col = (56, 189, 248, 60)  # Safe ray
                
            pygame.draw.line(ray_surf, col, (int(drone.x), int(drone.y)), (int(rx), int(ry)), 1)
            
        self.surface.blit(ray_surf, (0, 0))

    def _render_waypoint_path(self, drone):
        """Draws waypoint patrol route or investigation vector line for the drone."""
        if drone.state == DroneState.CHARGING:
            return

        if drone.state == DroneState.INVESTIGATE and drone.target_pos:
            # Draw vector vectoring line to target anomaly
            tx, ty = int(drone.target_pos[0]), int(drone.target_pos[1])
            pygame.draw.line(self.surface, COLOR_ACCENT_AMBER, (int(drone.x), int(drone.y)), (tx, ty), 2)
            pygame.draw.circle(self.surface, COLOR_ACCENT_RED, (tx, ty), 10, 2)

        # Waypoint dots
        if drone.waypoints and drone.state == DroneState.PATROL:
            for idx, (wx, wy) in enumerate(drone.waypoints):
                col = COLOR_ACCENT_AMBER if idx == drone.current_wp_index else (100, 130, 150)
                pygame.draw.circle(self.surface, col, (int(wx), int(wy)), 4)
                pygame.draw.circle(self.surface, col, (int(wx), int(wy)), 7, 1)

    def _render_drone(self, drone):
        """Draws quadcopter drone graphic, rotor blades, state indicator, and telemetry badge."""
        dx, dy = int(drone.x), int(drone.y)

        if drone.state == DroneState.CHARGING:
            # Draw charging icon at base
            pygame.draw.circle(self.surface, COLOR_BASE_DOCK, (dx, dy), 10)
            lbl = self.font_bold.render(f"CHARGING {int(drone.battery)}%", True, COLOR_TEXT_PRIMARY)
            self.surface.blit(lbl, (dx - lbl.get_width()//2, dy - 24))
            return

        if drone.state == DroneState.ANALYZE:
            # Draw a beautiful scanning reticle under the drone
            pulse = math.sin(pygame.time.get_ticks() * 0.015) * 5.0
            r = 30.0 + pulse
            # Draw crosshairs
            pygame.draw.circle(self.surface, COLOR_ACCENT_AMBER, (dx, dy), int(r), 1)
            pygame.draw.line(self.surface, COLOR_ACCENT_AMBER, (dx - r - 5, dy), (dx - r + 2, dy), 1)
            pygame.draw.line(self.surface, COLOR_ACCENT_AMBER, (dx + r - 2, dy), (dx + r + 5, dy), 1)
            pygame.draw.line(self.surface, COLOR_ACCENT_AMBER, (dx, dy - r - 5), (dx, dy - r + 2), 1)
            pygame.draw.line(self.surface, COLOR_ACCENT_AMBER, (dx, dy + r - 2), (dx, dy + r + 5), 1)
            
            # Draw progress arc (sweeping clockwise starting from the top)
            if drone.analysis_progress > 0:
                rect = pygame.Rect(dx - 22, dy - 22, 44, 44)
                start_rad = -math.pi / 2
                stop_rad = start_rad + max(0.05, (drone.analysis_progress / 100.0) * 2 * math.pi)
                pygame.draw.arc(self.surface, COLOR_ACCENT_GREEN, rect, start_rad, stop_rad, 3)

        # Quadcopter frame arms
        arm_len = 14
        angle = drone.heading

        # 4 Rotor arm angles
        for i in range(4):
            arm_angle = angle + (i * math.pi / 2.0) + (math.pi / 4.0)
            rx = dx + math.cos(arm_angle) * arm_len
            ry = dy + math.sin(arm_angle) * arm_len
            pygame.draw.line(self.surface, (200, 220, 240), (dx, dy), (rx, ry), 2)
            
            # Spinning Rotor Blade circle
            spin_r = 5
            pygame.draw.circle(self.surface, drone.color, (int(rx), int(ry)), spin_r, 1)

        # Central Drone Body Core
        pygame.draw.circle(self.surface, (30, 41, 59), (dx, dy), 8)
        pygame.draw.circle(self.surface, drone.color, (dx, dy), 6)

        # Front Heading Indicator
        hx = dx + math.cos(angle) * 16
        hy = dy + math.sin(angle) * 16
        pygame.draw.circle(self.surface, COLOR_ACCENT_AMBER, (int(hx), int(hy)), 3)

        # Drone ID & State Badge
        state_col = COLOR_ACCENT_GREEN
        state_text = drone.state
        if drone.state == DroneState.INVESTIGATE:
            state_col = COLOR_ACCENT_AMBER
        elif drone.state == DroneState.ANALYZE:
            state_col = COLOR_ACCENT_AMBER
            state_text = f"ANALYZING {int(drone.analysis_progress)}%"
        elif drone.state == DroneState.RETURN_TO_BASE:
            state_col = COLOR_ACCENT_RED

        id_text = self.font_bold.render(f"{drone.drone_id} [{state_text}]", True, state_col)
        gps_text = self.font_sm.render(drone.gps_string, True, (200, 220, 240))

        # Text background badge box
        badge_w = max(id_text.get_width(), gps_text.get_width()) + 10
        badge_surf = pygame.Surface((badge_w, 28), pygame.SRCALPHA)
        badge_surf.fill((15, 23, 42, 210))
        pygame.draw.rect(badge_surf, (51, 65, 85), badge_surf.get_rect(), 1, border_radius=4)
        
        self.surface.blit(badge_surf, (dx - badge_w//2, dy - 42))
        self.surface.blit(id_text, (dx - id_text.get_width()//2, dy - 40))
        self.surface.blit(gps_text, (dx - gps_text.get_width()//2, dy - 27))

    def _render_alert_pins(self, env):
        """Draws alert marker flags on detected fires."""
        for fire in env.fires:
            if fire.alert_sent:
                fx, fy = int(fire.x), int(fire.y)
                # Pin pole
                pygame.draw.line(self.surface, (248, 113, 113), (fx, fy), (fx, fy - 22), 2)
                # Pin flag
                points = [(fx, fy - 22), (fx + 14, fy - 16), (fx, fy - 10)]
                pygame.draw.polygon(self.surface, (239, 68, 68), points)
                
                flag_lbl = self.font_sm.render("ALERT", True, COLOR_TEXT_PRIMARY)
                self.surface.blit(flag_lbl, (fx + 16, fy - 22))
