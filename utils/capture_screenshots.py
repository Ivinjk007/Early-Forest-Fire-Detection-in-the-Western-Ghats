"""
Automated Screenshot Generator Utility.
Runs the simulation for a brief period and exports high-resolution screenshots for technical documentation and assignment reports.
"""

import os
import sys
import pygame

# Set dummy video driver for headless environment if needed, or normal Pygame export
os.environ["SDL_VIDEODRIVER"] = "dummy"

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import WINDOW_WIDTH, WINDOW_HEIGHT, COLOR_BG_DARK
from models.environment import Environment
from models.drone import AutonomousDrone
from ui.renderer import EnvironmentRenderer
from ui.dashboard import DashboardHUD
from main import create_patrol_drones

def generate_screenshots():
    """Generates simulation screenshots and saves them to docs/assets/ directory."""
    pygame.init()
    pygame.font.init()
    
    screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    
    env = Environment()
    drones = create_patrol_drones()
    renderer = EnvironmentRenderer(screen)
    hud = DashboardHUD(screen)

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "assets")
    os.makedirs(output_dir, os.path.ok if hasattr(os, "path_ok") else True, exist_ok=True)

    print(f"[SCREENSHOT UTILITY] Simulating frames and generating screenshots in {output_dir}...")

    # Ignite a secondary wildfire scenario for rich visuals
    env.ignite_fire(340, 520, temp_c=420.0, is_user=True)
    env.ignite_fire(720, 240, temp_c=580.0, is_user=True)

    # Step simulation 90 frames
    for frame in range(120):
        env.update()
        for drone in drones:
            alert = drone.update(env)
            if alert:
                hud.add_alert(alert)

        # Render pass
        screen.fill(COLOR_BG_DARK)
        renderer.render(env, drones, show_thermal_overlay=True, show_raycast=True)
        hud.render(drones, env, show_thermal=True, show_raycast=True)

    # Save full view screenshot
    full_path = os.path.join(output_dir, "simulation_overview.png")
    pygame.image.save(screen, full_path)
    print(f" -> Saved: {full_path}")

    # Step simulation 60 more frames with thermal-only highlight
    for frame in range(60):
        env.update()
        for drone in drones:
            drone.update(env)

        screen.fill(COLOR_BG_DARK)
        renderer.render(env, drones, show_thermal_overlay=True, show_raycast=False)
        hud.render(drones, env, show_thermal=True, show_raycast=False)

    thermal_path = os.path.join(output_dir, "thermal_detection_mode.png")
    pygame.image.save(screen, thermal_path)
    print(f" -> Saved: {thermal_path}")

    print("[SCREENSHOT UTILITY] Screenshot generation complete!")

if __name__ == "__main__":
    generate_screenshots()
