"""
Control Station Telemetry Dashboard HUD.
Displays live telemetry cards, thermal heat matrix widget, system metrics, and real-time alert feed.
"""

import time
import math
import pygame
import numpy as np
from config import (
    MAP_WIDTH, HUD_WIDTH, HUD_HEIGHT, COLOR_BG_DARK, COLOR_PANEL_BG,
    COLOR_PANEL_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_ACCENT_BLUE,
    COLOR_ACCENT_GREEN, COLOR_ACCENT_AMBER, COLOR_ACCENT_RED, SEVERITY_CRITICAL,
    SEVERITY_MEDIUM, SEVERITY_LOW
)
from models.drone import DroneState

class DashboardHUD:
    """Renders real-time telemetry panel, thermal camera feed, system stats, and alert logs."""
    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self.x_offset = MAP_WIDTH
        self.width = HUD_WIDTH
        self.height = HUD_HEIGHT

        # Fonts
        self.font_title = pygame.font.SysFont("Segoe UI", 16, bold=True)
        self.font_section = pygame.font.SysFont("Segoe UI", 14, bold=True)
        self.font_body = pygame.font.SysFont("Segoe UI", 12)
        self.font_bold = pygame.font.SysFont("Segoe UI", 12, bold=True)
        self.font_small = pygame.font.SysFont("Segoe UI", 11)

        # Alert Log Feed
        self.alerts_feed: list[dict] = []
        self.max_alerts = 6
        self.selected_drone_index = 0

        # Interactive UI Button Rectangles
        self.buttons = {}
        self._setup_buttons()

    def _setup_buttons(self):
        """Creates interactive button boundaries."""
        btn_y = self.height - 110
        btn_w = (self.width - 40) // 2
        
        self.buttons['ignite'] = pygame.Rect(self.x_offset + 15, btn_y, btn_w, 34)
        self.buttons['thermal_toggle'] = pygame.Rect(self.x_offset + 25 + btn_w, btn_y, btn_w, 34)
        self.buttons['raycast_toggle'] = pygame.Rect(self.x_offset + 15, btn_y + 42, btn_w, 34)
        self.buttons['rtb_all'] = pygame.Rect(self.x_offset + 25 + btn_w, btn_y + 42, btn_w, 34)

    def add_alert(self, alert_data: dict):
        """Pushes a new emergency alert to the control console, avoiding duplicates and updating in place."""
        current_time = time.time()
        for prev in self.alerts_feed:
            # Calculate distance between pixel positions of the hotspots
            dist = math.hypot(prev['pixel_pos'][0] - alert_data['pixel_pos'][0],
                              prev['pixel_pos'][1] - alert_data['pixel_pos'][1])
            time_diff = current_time - prev.get('timestamp_raw', 0)
            if dist < 60.0 and time_diff < 8.0:
                # Update peak temperature and confidence in place if it gets more severe
                if alert_data['peak_temp'] > prev['peak_temp']:
                    prev['peak_temp'] = alert_data['peak_temp']
                    prev['confidence'] = alert_data['confidence']
                    prev['time_str'] = time.strftime("%H:%M:%S")
                    prev['timestamp_raw'] = current_time
                return

        alert_data['time_str'] = time.strftime("%H:%M:%S")
        alert_data['timestamp_raw'] = current_time
        self.alerts_feed.insert(0, alert_data)
        if len(self.alerts_feed) > self.max_alerts:
            self.alerts_feed.pop()

    def render(self, drones: list, env, show_thermal: bool, show_raycast: bool):
        """Renders dashboard HUD layout."""
        # Background Panel
        hud_rect = pygame.Rect(self.x_offset, 0, self.width, self.height)
        pygame.draw.rect(self.surface, COLOR_PANEL_BG, hud_rect)
        pygame.draw.line(self.surface, COLOR_PANEL_BORDER, (self.x_offset, 0), (self.x_offset, self.height), 2)

        # 1. Header Banner
        self._render_header(env)

        # 2. System Overview Stats Cards
        self._render_system_stats(drones, env)

        # 3. Live Drone Telemetry Cards
        self._render_drone_telemetry_cards(drones)

        # 4. Thermal Camera Feed Widget
        if drones:
            selected_drone = drones[self.selected_drone_index % len(drones)]
            self._render_thermal_widget(selected_drone)

        # 5. Emergency Alert Feed
        self._render_alert_feed()

        # 6. Control Action Buttons
        self._render_control_buttons(show_thermal, show_raycast, drones)

    def _render_header(self, env):
        """Header title and live clock."""
        header_rect = pygame.Rect(self.x_offset + 10, 10, self.width - 20, 52)
        pygame.draw.rect(self.surface, COLOR_BG_DARK, header_rect, border_radius=6)
        pygame.draw.rect(self.surface, COLOR_PANEL_BORDER, header_rect, 1, border_radius=6)

        title = self.font_title.render("WESTERN GHATS AI CONTROL", True, COLOR_TEXT_PRIMARY)
        subtitle = self.font_small.render("Nilgiri Sector • Autonomous Drone Patrol", True, COLOR_ACCENT_BLUE)
        clock_str = time.strftime("%Y-%m-%d %H:%M:%S")
        clock_lbl = self.font_small.render(clock_str, True, COLOR_TEXT_MUTED)

        self.surface.blit(title, (self.x_offset + 20, 16))
        self.surface.blit(subtitle, (self.x_offset + 20, 38))
        self.surface.blit(clock_lbl, (self.x_offset + self.width - 20 - clock_lbl.get_width(), 18))

    def _render_system_stats(self, drones: list, env):
        """Summary metrics grid (Active Drones, Wildfires, Alerts, Risk Level)."""
        card_w = (self.width - 40) // 3
        card_y = 70
        
        active_fires = sum(1 for f in env.fires if f.active)
        risk_level = "CRITICAL" if active_fires > 1 else ("ELEVATED" if active_fires == 1 else "NORMAL")
        risk_col = COLOR_ACCENT_RED if active_fires > 1 else (COLOR_ACCENT_AMBER if active_fires == 1 else COLOR_ACCENT_GREEN)

        stats = [
            ("DRONES", f"{len(drones)} Active", COLOR_ACCENT_BLUE),
            ("WILDFIRES", f"{active_fires} Detected", COLOR_ACCENT_RED if active_fires > 0 else COLOR_ACCENT_GREEN),
            ("SECTOR RISK", risk_level, risk_col)
        ]

        for i, (label, val, col) in enumerate(stats):
            cx = self.x_offset + 15 + i * (card_w + 5)
            c_rect = pygame.Rect(cx, card_y, card_w, 48)
            pygame.draw.rect(self.surface, COLOR_BG_DARK, c_rect, border_radius=4)
            pygame.draw.rect(self.surface, COLOR_PANEL_BORDER, c_rect, 1, border_radius=4)

            lbl_txt = self.font_small.render(label, True, COLOR_TEXT_MUTED)
            val_txt = self.font_bold.render(val, True, col)

            self.surface.blit(lbl_txt, (cx + 8, card_y + 6))
            self.surface.blit(val_txt, (cx + 8, card_y + 24))

    def _render_drone_telemetry_cards(self, drones: list):
        """Individual cards for each drone's battery, state, GPS, speed."""
        section_lbl = self.font_section.render("DRONE TELEMETRY & SENSORS", True, COLOR_TEXT_PRIMARY)
        self.surface.blit(section_lbl, (self.x_offset + 15, 128))

        card_y = 150
        card_h = 72
        
        for i, drone in enumerate(drones):
            cy = card_y + i * (card_h + 6)
            c_rect = pygame.Rect(self.x_offset + 15, cy, self.width - 30, card_h)
            
            # Selection highlight
            is_selected = (i == self.selected_drone_index % len(drones))
            border_col = COLOR_ACCENT_BLUE if is_selected else COLOR_PANEL_BORDER
            
            pygame.draw.rect(self.surface, COLOR_BG_DARK, c_rect, border_radius=6)
            pygame.draw.rect(self.surface, border_col, c_rect, 2 if is_selected else 1, border_radius=6)

            # Drone Header ID & State Badge
            id_txt = self.font_bold.render(drone.drone_id, True, drone.color)
            
            state_col = COLOR_ACCENT_GREEN
            state_text = drone.state
            if drone.state == DroneState.INVESTIGATE:
                state_col = COLOR_ACCENT_AMBER
            elif drone.state == DroneState.ANALYZE:
                state_col = COLOR_ACCENT_AMBER
                state_text = f"ANALYZING {int(drone.analysis_progress)}%"
            elif drone.state in (DroneState.RETURN_TO_BASE, DroneState.CHARGING):
                state_col = COLOR_ACCENT_RED
                
            state_badge = self.font_small.render(state_text, True, state_col)
            self.surface.blit(id_txt, (self.x_offset + 25, cy + 8))
            self.surface.blit(state_badge, (self.x_offset + 25 + id_txt.get_width() + 10, cy + 10))

            # Battery Bar
            bat_pct = drone.battery
            bat_col = COLOR_ACCENT_GREEN if bat_pct > 50 else (COLOR_ACCENT_AMBER if bat_pct > 22 else COLOR_ACCENT_RED)
            
            bat_lbl = self.font_small.render(f"BAT: {int(bat_pct)}%", True, bat_col)
            self.surface.blit(bat_lbl, (self.x_offset + self.width - 120, cy + 8))
            
            # Battery Bar Rect
            bat_bar_rect = pygame.Rect(self.x_offset + self.width - 120, cy + 24, 95, 6)
            pygame.draw.rect(self.surface, (51, 65, 85), bat_bar_rect, border_radius=3)
            fill_w = int(95 * (bat_pct / 100.0))
            if fill_w > 0:
                pygame.draw.rect(self.surface, bat_col, pygame.Rect(self.x_offset + self.width - 120, cy + 24, fill_w, 6), border_radius=3)

            # Telemetry Metrics (GPS, Speed, Thermal)
            gps_txt = self.font_small.render(f"GPS: {drone.gps_string}", True, COLOR_TEXT_MUTED)
            spd_txt = self.font_small.render(f"SPD: {drone.speed:.1f} m/s", True, COLOR_TEXT_MUTED)
            temp_txt = self.font_small.render(f"THERMAL: {drone.smoothed_peak_temp:.1f}°C", True, COLOR_ACCENT_AMBER if drone.smoothed_peak_temp > 50 else COLOR_TEXT_MUTED)

            self.surface.blit(gps_txt, (self.x_offset + 25, cy + 32))
            self.surface.blit(spd_txt, (self.x_offset + 25, cy + 48))
            self.surface.blit(temp_txt, (self.x_offset + 210, cy + 48))

    def _render_thermal_widget(self, drone):
        """Displays simulated 12x12 thermal heat pixel camera array."""
        widget_y = 390
        w_rect = pygame.Rect(self.x_offset + 15, widget_y, self.width - 30, 145)
        pygame.draw.rect(self.surface, COLOR_BG_DARK, w_rect, border_radius=6)
        pygame.draw.rect(self.surface, COLOR_PANEL_BORDER, w_rect, 1, border_radius=6)

        title = self.font_section.render(f"THERMAL CAMERA FEED ({drone.drone_id})", True, COLOR_TEXT_PRIMARY)
        self.surface.blit(title, (self.x_offset + 25, widget_y + 8))

        # Thermal Matrix Heatmap rendering (12x12 grid)
        matrix = drone.thermal_cam.last_thermal_matrix
        grid_size = 12
        cell_size = 8
        grid_start_x = self.x_offset + 25
        grid_start_y = widget_y + 34

        for r in range(grid_size):
            for c in range(grid_size):
                temp = matrix[r, c]
                # Heat Color Mapping: 24°C (Dark Blue) -> 50°C (Green) -> 150°C (Yellow) -> 400°C+ (Bright Red)
                if temp < 35.0:
                    col = (20, 50, 110)
                elif temp < 50.0:
                    col = (34, 197, 94)
                elif temp < 150.0:
                    col = (251, 191, 36)
                else:
                    col = (239, 68, 68)

                cell_rect = pygame.Rect(grid_start_x + c * (cell_size + 1), grid_start_y + r * (cell_size + 1), cell_size, cell_size)
                pygame.draw.rect(self.surface, col, cell_rect)

        # Thermal Feed Stats
        stats_x = grid_start_x + grid_size * (cell_size + 1) + 20
        lbl_peak = self.font_body.render(f"PEAK TEMP: {drone.smoothed_peak_temp:.1f}°C", True, COLOR_ACCENT_RED if drone.smoothed_peak_temp > 100 else COLOR_TEXT_PRIMARY)
        lbl_avg = self.font_body.render(f"AVG TEMP:  {drone.smoothed_avg_temp:.1f}°C", True, COLOR_TEXT_MUTED)
        lbl_std = self.font_body.render(f"HEAT VARIANCE: {drone.smoothed_std_temp:.1f}", True, COLOR_TEXT_MUTED)
        
        status_str = "NORMAL SCAN"
        status_col = COLOR_ACCENT_GREEN
        if drone.smoothed_peak_temp >= 200.0:
            status_str = "WILDFIRE DETECTED!"
            status_col = COLOR_ACCENT_RED
        elif drone.smoothed_peak_temp >= 50.0:
            status_str = "HOTSPOT ANOMALY"
            status_col = COLOR_ACCENT_AMBER

        lbl_status = self.font_bold.render(f"STATUS: {status_str}", True, status_col)

        self.surface.blit(lbl_peak, (stats_x, grid_start_y))
        self.surface.blit(lbl_avg, (stats_x, grid_start_y + 20))
        self.surface.blit(lbl_std, (stats_x, grid_start_y + 40))
        self.surface.blit(lbl_status, (stats_x, grid_start_y + 68))

    def _render_alert_feed(self):
        """Displays real-time emergency alert feed showing all detected fires simultaneously."""
        feed_y = 548
        f_rect = pygame.Rect(self.x_offset + 15, feed_y, self.width - 30, 185)
        pygame.draw.rect(self.surface, COLOR_BG_DARK, f_rect, border_radius=6)
        pygame.draw.rect(self.surface, COLOR_PANEL_BORDER, f_rect, 1, border_radius=6)

        title = self.font_section.render("EMERGENCY ALERT LOG FEED", True, COLOR_ACCENT_RED)
        self.surface.blit(title, (self.x_offset + 25, feed_y + 8))

        if not self.alerts_feed:
            empty_lbl = self.font_small.render("No emergency alerts currently active. Patrol status nominal.", True, COLOR_TEXT_MUTED)
            self.surface.blit(empty_lbl, (self.x_offset + 25, feed_y + 35))
            return

        # Render Table Headers
        header_y = feed_y + 32
        lbl_time_h = self.font_bold.render("TIME", True, COLOR_TEXT_MUTED)
        lbl_drone_h = self.font_bold.render("DRONE", True, COLOR_TEXT_MUTED)
        lbl_loc_h = self.font_bold.render("LOCATION (GPS)", True, COLOR_TEXT_MUTED)
        lbl_temp_h = self.font_bold.render("TEMP", True, COLOR_TEXT_MUTED)
        lbl_sev_h = self.font_bold.render("SEVERITY", True, COLOR_TEXT_MUTED)

        self.surface.blit(lbl_time_h, (self.x_offset + 25, header_y))
        self.surface.blit(lbl_drone_h, (self.x_offset + 85, header_y))
        self.surface.blit(lbl_loc_h, (self.x_offset + 175, header_y))
        self.surface.blit(lbl_temp_h, (self.x_offset + 325, header_y))
        self.surface.blit(lbl_sev_h, (self.x_offset + 380, header_y))

        # Divider line under header
        pygame.draw.line(self.surface, COLOR_PANEL_BORDER, (self.x_offset + 20, header_y + 18), (self.x_offset + self.width - 20, header_y + 18), 1)

        # Render rows (up to 6 rows fits beautifully)
        row_y = header_y + 24
        for idx, alert in enumerate(self.alerts_feed[:6]):
            y_pos = row_y + idx * 20
            
            # Severity configuration
            if alert['severity'] == SEVERITY_CRITICAL:
                sev_col = COLOR_ACCENT_RED
                sev_str = "CRITICAL"
            elif alert['severity'] == SEVERITY_MEDIUM:
                sev_col = COLOR_ACCENT_AMBER
                sev_str = "MEDIUM"
            else:
                sev_col = COLOR_ACCENT_GREEN
                sev_str = "LOW"

            lbl_time = self.font_body.render(alert['time_str'], True, COLOR_TEXT_PRIMARY)
            lbl_drone = self.font_body.render(alert['drone_id'], True, COLOR_TEXT_PRIMARY)
            lbl_loc = self.font_body.render(alert['gps_str'], True, COLOR_TEXT_PRIMARY)
            lbl_temp = self.font_body.render(f"{int(alert['peak_temp'])}°C", True, COLOR_TEXT_PRIMARY)
            lbl_sev = self.font_bold.render(sev_str, True, sev_col)

            self.surface.blit(lbl_time, (self.x_offset + 25, y_pos))
            self.surface.blit(lbl_drone, (self.x_offset + 85, y_pos))
            self.surface.blit(lbl_loc, (self.x_offset + 175, y_pos))
            self.surface.blit(lbl_temp, (self.x_offset + 325, y_pos))
            self.surface.blit(lbl_sev, (self.x_offset + 380, y_pos))

    def _render_control_buttons(self, show_thermal: bool, show_raycast: bool, drones: list):
        """Draws interactive buttons at the bottom of the HUD panel."""
        any_recalled = any(d.manual_recall for d in drones) if drones else False
        rtb_text = "RESUME ALL" if any_recalled else "RECALL ALL (RTB)"
        rtb_color = COLOR_ACCENT_GREEN if any_recalled else COLOR_ACCENT_AMBER

        btn_configs = [
            ('ignite', "IGNITE WILDFIRE", COLOR_ACCENT_RED),
            ('thermal_toggle', "THERMAL: ON" if show_thermal else "THERMAL: OFF", COLOR_ACCENT_AMBER if show_thermal else COLOR_TEXT_MUTED),
            ('raycast_toggle', "RAYCAST: ON" if show_raycast else "RAYCAST: OFF", COLOR_ACCENT_BLUE if show_raycast else COLOR_TEXT_MUTED),
            ('rtb_all', rtb_text, rtb_color)
        ]

        for key, text, col in btn_configs:
            rect = self.buttons[key]
            pygame.draw.rect(self.surface, COLOR_BG_DARK, rect, border_radius=4)
            pygame.draw.rect(self.surface, col, rect, 1, border_radius=4)

            lbl = self.font_bold.render(text, True, col)
            self.surface.blit(lbl, (rect.x + (rect.width - lbl.get_width())//2, rect.y + 8))

    def handle_click(self, pos: tuple[int, int], drones: list, env) -> str | None:
        """Handles dashboard mouse click events for buttons or drone selection."""
        mx, my = pos
        
        # Check drone card selection clicks
        if self.x_offset + 15 <= mx <= self.x_offset + self.width - 15:
            card_y = 150
            for i in range(len(drones)):
                cy = card_y + i * 78
                if cy <= my <= cy + 72:
                    self.selected_drone_index = i
                    return "DRONE_SELECTED"

        # Check Action Buttons
        for key, rect in self.buttons.items():
            if rect.collidepoint(mx, my):
                return key

        return None
