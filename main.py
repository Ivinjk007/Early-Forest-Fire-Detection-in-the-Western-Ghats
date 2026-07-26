"""
Western Ghats Autonomous AI Forest Fire Detection Simulation.
Main entry point. Coordinates drone physics, AI finite state machines, thermal sensors, and Control Station HUD.
"""

import sys
import math
import random
import pygame

from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, MAP_WIDTH, MAP_HEIGHT, FPS,
    COLOR_BG_DARK, DRONE_COLORS
)
from models.environment import Environment
from models.drone import AutonomousDrone, DroneState
from ui.renderer import EnvironmentRenderer
from ui.dashboard import DashboardHUD

def create_patrol_drones() -> list[AutonomousDrone]:
    """Creates 3 autonomous patrol drones with dedicated non-overlapping waypoint routes across Western Ghats."""
    # Drone Alpha - Western Sector Patrol
    waypoints_alpha = [(150, 150), (420, 140), (320, 380), (120, 360)]
    drone_a = AutonomousDrone("DRONE ALPHA", start_pos=(120, 120), waypoints=waypoints_alpha, color=DRONE_COLORS[0])

    # Drone Beta - Central & Eastern Ridge Patrol
    waypoints_beta = [(500, 140), (840, 150), (820, 420), (520, 390)]
    drone_b = AutonomousDrone("DRONE BETA", start_pos=(520, 120), waypoints=waypoints_beta, color=DRONE_COLORS[1])

    # Drone Gamma - Southern Valley Patrol
    waypoints_gamma = [(200, 560), (480, 580), (780, 680), (220, 700)]
    drone_c = AutonomousDrone("DRONE GAMMA", start_pos=(180, 550), waypoints=waypoints_gamma, color=DRONE_COLORS[2])

    return [drone_a, drone_b, drone_c]


def main():
    """Main simulation loop."""
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("AI Forest Fire Detection Simulation - Western Ghats Sector")
    clock = pygame.time.Clock()

    # Instantiate Simulation Models & UI Renderers
    env = Environment()
    drones = create_patrol_drones()
    renderer = EnvironmentRenderer(screen)
    hud = DashboardHUD(screen)

    # UI View Toggles
    show_thermal_overlay = True
    show_raycast_lines = True

    running = True

    print("===================================================================")
    print("  WESTERN GHATS AUTONOMOUS AI FOREST FIRE DETECTION SIMULATION")
    print("  Press 'SPACE' or click on map to ignite a fire.")
    print("  Press 'T' to toggle thermal FOV scanner view.")
    print("  Press 'R' to toggle raycast obstacle sensor lines.")
    print("  Press 'B' to order all drones to Return to Base (RTB).")
    print("===================================================================")

    while running:
        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    # Ignite fire at random location
                    rx = random.uniform(100, MAP_WIDTH - 100)
                    ry = random.uniform(100, MAP_HEIGHT - 100)
                    env.ignite_fire(rx, ry, temp_c=random.uniform(340.0, 550.0), is_user=True)
                    print(f"[EVENT] Wildfire ignited at ({rx:.0f}, {ry:.0f})")
                elif event.key == pygame.K_t:
                    show_thermal_overlay = not show_thermal_overlay
                elif event.key == pygame.K_r:
                    show_raycast_lines = not show_raycast_lines
                elif event.key == pygame.K_b:
                    # Toggle recall for ALL drones
                    any_recalled = any(d.manual_recall for d in drones)
                    if any_recalled:
                        print("[COMMAND] Resuming autonomous patrol for ALL drones.")
                        for drone in drones:
                            drone.resume_patrol()
                    else:
                        print("[COMMAND] Recall (RTB) signal sent to ALL drones. Returning to base dock...")
                        for drone in drones:
                            drone.recall_to_base(env)
                elif event.key == pygame.K_p:
                    # Toggle recall for currently selected drone only
                    selected_drone = drones[hud.selected_drone_index % len(drones)]
                    if selected_drone.manual_recall:
                        print(f"[COMMAND] Resuming autonomous patrol for {selected_drone.drone_id}.")
                        selected_drone.resume_patrol()
                    else:
                        print(f"[COMMAND] Recall (RTB) signal sent to {selected_drone.drone_id}. Returning to base dock...")
                        selected_drone.recall_to_base(env)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                if mx < MAP_WIDTH:
                    # Click on map -> If click is near an active fire, close it, else ignite new fire
                    closed_any = False
                    for fire in env.fires:
                        if fire.active and math.hypot(fire.x - mx, fire.y - my) < 25.0:
                            fire.active = False
                            closed_any = True
                            print(f"[USER ACTION] Closed fire at ({fire.x:.1f}, {fire.y:.1f})")
                            break
                    if not closed_any:
                        env.ignite_fire(mx, my, temp_c=random.uniform(360.0, 600.0), is_user=True)
                        print(f"[USER ACTION] Ignition command at map pixel ({mx}, {my})")
                else:
                    # Click on Dashboard HUD -> Handle HUD Buttons
                    action = hud.handle_click((mx, my), drones, env)
                    if action == 'ignite':
                        rx = random.uniform(100, MAP_WIDTH - 100)
                        ry = random.uniform(100, MAP_HEIGHT - 100)
                        env.ignite_fire(rx, ry, temp_c=random.uniform(350.0, 550.0), is_user=True)
                    elif action == 'thermal_toggle':
                        show_thermal_overlay = not show_thermal_overlay
                    elif action == 'raycast_toggle':
                        show_raycast_lines = not show_raycast_lines
                    elif action == 'rtb_all':
                        # Toggle recall for ALL drones
                        any_recalled = any(d.manual_recall for d in drones)
                        if any_recalled:
                            print("[COMMAND] Resuming autonomous patrol for ALL drones.")
                            for drone in drones:
                                drone.resume_patrol()
                        else:
                            print("[COMMAND] Recall (RTB) signal sent to ALL drones. Returning to base dock...")
                            for drone in drones:
                                drone.recall_to_base(env)

        # 2. Simulation Step
        env.update()

        # Update each autonomous drone
        for drone in drones:
            alert = drone.update(env)
            if alert:
                # Fire alert detected by drone AI
                hud.add_alert(alert)

                # Mark fire spot alert sent
                for fire in env.fires:
                    if math.hypot(fire.x - alert['pixel_pos'][0], fire.y - alert['pixel_pos'][1]) < 40.0:
                        fire.alert_sent = True

        # 3. Graphics Rendering
        screen.fill(COLOR_BG_DARK)

        # Render 2D Forest Viewport
        renderer.render(env, drones, show_thermal_overlay=show_thermal_overlay, show_raycast=show_raycast_lines)

        # Render Control Station Dashboard HUD
        hud.render(drones, env, show_thermal=show_thermal_overlay, show_raycast=show_raycast_lines)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
