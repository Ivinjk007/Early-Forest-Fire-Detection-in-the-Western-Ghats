"""
Western Ghats Environment Model.
Simulates terrain elevation (hills/trees), thermal heat map, river stream, and dynamic fire propagation.
"""

import math
import random
import numpy as np
from config import (
    MAP_WIDTH, MAP_HEIGHT, TEMP_AMBIENT_MIN, TEMP_AMBIENT_MAX,
    TEMP_CONFIRMED_FIRE_MIN, TEMP_MAX, COLOR_HILL_BASE, COLOR_HILL_PEAK
)
from utils.geo import pixel_to_gps

class HillObstacle:
    """Represents a mountain hill or ridge obstacle in the Western Ghats."""
    def __init__(self, x: float, y: float, radius: float, height_m: float):
        self.x = x
        self.y = y
        self.radius = radius
        self.height_m = height_m # Elevation height in meters

    def contains(self, px: float, py: float, margin: float = 0.0) -> bool:
        dist = math.hypot(px - self.x, py - self.y)
        return dist <= (self.radius + margin)


class FireSpot:
    """Represents an active fire hotspot with temperature, intensity, smoke, and growth."""
    def __init__(self, x: float, y: float, temp_c: float = 350.0, is_user_ignited: bool = False):
        self.x = x
        self.y = y
        self.temp_c = temp_c
        self.is_user_ignited = is_user_ignited
        self.radius = 18.0
        self.smoke_density = 0.75
        self.growth_rate = 0.15 # Temperature gain per frame
        self.active = True
        self.classified = False
        self.alert_sent = False
        self.gps_lat, self.gps_lon = pixel_to_gps(x, y)

    def update(self):
        """Simulates fire growth and temperature fluctuations."""
        if self.active:
            if self.temp_c < TEMP_MAX:
                self.temp_c += self.growth_rate
            self.radius = min(60.0, 18.0 + (self.temp_c - TEMP_CONFIRMED_FIRE_MIN) * 0.05)
            self.smoke_density = min(1.0, 0.4 + (self.temp_c / TEMP_MAX) * 0.6)


class Environment:
    """Main Environment simulation handling Western Ghats terrain, heat matrix, and fires."""
    def __init__(self, width: int = MAP_WIDTH, height: int = MAP_HEIGHT):
        self.width = width
        self.height = height
        
        # Base Station Dock position (bottom-left forest outpost)
        self.base_station = (90.0, height - 90.0)

        # Generate Terrain Obstacles (Hills / Mountain Ridges characteristic of Nilgiris)
        self.hills = [
            HillObstacle(240, 200, 75, 1400),
            HillObstacle(580, 160, 90, 1800),
            HillObstacle(750, 480, 110, 2100),
            HillObstacle(360, 520, 85, 1650),
            HillObstacle(160, 420, 65, 1200),
            HillObstacle(520, 680, 70, 1350)
        ]

        # River Stream Points (representing Kabini/Bhavani river curves)
        self.river_path = [
            (0, 300), (150, 320), (300, 280), (450, 350), 
            (600, 330), (750, 410), (MAP_WIDTH, 390)
        ]

        # Thermal Heat Grid (Downsampled matrix for performance)
        self.grid_scale = 10 # 1 cell = 10x10 pixels
        self.grid_w = width // self.grid_scale
        self.grid_h = height // self.grid_scale
        
        # Initialize Ambient Temperature Field
        self.temp_grid = np.random.uniform(
            TEMP_AMBIENT_MIN, TEMP_AMBIENT_MAX, (self.grid_h, self.grid_w)
        )
        
        # Add natural thermal variation (e.g. sun-baked rocks)
        self._seed_thermal_variations()

        # Active Fires List & Smoke Particles
        self.fires: list[FireSpot] = []
        self.particles: list[dict] = []
        
        # Seed initial wildfire scenario for realistic demo
        # self.ignite_fire(680, 260, temp_c=320.0) # Primary fire hotspot in eastern ridge

    def _seed_thermal_variations(self):
        """Creates realistic ambient thermal variation across different terrain features."""
        # Rock patches (slight thermal anomalies 40-48°C)
        rock_patches = [(300, 120), (820, 220), (450, 600)]
        for rx, ry in rock_patches:
            gx, gy = rx // self.grid_scale, ry // self.grid_scale
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    if 0 <= gy+dy < self.grid_h and 0 <= gx+dx < self.grid_w:
                        self.temp_grid[gy+dy, gx+dx] += random.uniform(8.0, 14.0)

    def ignite_fire(self, x: float, y: float, temp_c: float = 300.0, is_user: bool = False) -> FireSpot:
        """Ignites a new fire at the given map coordinates."""
        # Ensure within map bounds
        x = max(20.0, min(self.width - 20.0, x))
        y = max(20.0, min(self.height - 20.0, y))

        fire = FireSpot(x, y, temp_c=temp_c, is_user_ignited=is_user)
        self.fires.append(fire)
        return fire

    def get_temperature_at(self, x: float, y: float) -> float:
        """Calculates exact thermal reading at any pixel coordinate including long-range heat plumes."""
        gx = int(max(0, min(self.grid_w - 1, x // self.grid_scale)))
        gy = int(max(0, min(self.grid_h - 1, y // self.grid_scale)))
        
        base_temp = float(self.temp_grid[gy, gx])
        
        # Add thermal influence from active fires (Core heat + Long-range thermal plume)
        fire_temp_bonus = 0.0
        for fire in self.fires:
            if fire.active:
                dist = math.hypot(x - fire.x, y - fire.y)
                
                # 1. Intense Core Thermal Zone
                core_radius = max(75.0, fire.radius * 4.0)
                if dist < core_radius:
                    falloff = max(0.0, 1.0 - (dist / core_radius))
                    fire_temp_bonus += (fire.temp_c - base_temp) * (falloff ** 1.5)
                
                # 2. Long-Range Thermal Plume & Updraft Dispersion Zone (up to 380px radius)
                plume_radius = 380.0
                if dist < plume_radius:
                    plume_falloff = max(0.0, 1.0 - (dist / plume_radius))
                    # Adds 15-45°C thermal anomaly plume signal detectible by drone AI sensors
                    fire_temp_bonus += 38.0 * (plume_falloff ** 2)

        return base_temp + fire_temp_bonus

    def is_obstacle(self, x: float, y: float, margin: float = 15.0) -> bool:
        """Checks if a coordinate collides with any hill elevation obstacle."""
        for hill in self.hills:
            if hill.contains(x, y, margin=margin):
                return True
        return False

    def update(self):
        """Updates environment frame state, fire growth, smoke particles, and heat grid."""
        # Update active fires
        for fire in self.fires:
            fire.update()
            
            # Update grid heat around fire
            gx = int(fire.x // self.grid_scale)
            gy = int(fire.y // self.grid_scale)
            if 0 <= gy < self.grid_h and 0 <= gx < self.grid_w:
                self.temp_grid[gy, gx] = max(self.temp_grid[gy, gx], fire.temp_c * 0.85)

            # Spawn smoke particles
            if random.random() < 0.6:
                self.particles.append({
                    'x': fire.x + random.uniform(-8, 8),
                    'y': fire.y + random.uniform(-8, 8),
                    'vx': random.uniform(0.2, 0.8), # Wind drifting north-east
                    'vy': random.uniform(-1.2, -0.4), # Floating up
                    'radius': random.uniform(3.0, 7.0),
                    'alpha': 200,
                    'type': 'smoke' if random.random() < 0.7 else 'fire'
                })

        # Update floating particles
        for p in list(self.particles):
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['alpha'] -= 3.5
            p['radius'] += 0.15
            if p['alpha'] <= 0:
                self.particles.remove(p)
