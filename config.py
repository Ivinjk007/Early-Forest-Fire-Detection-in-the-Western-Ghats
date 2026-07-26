"""
Western Ghats AI Forest Fire Detection Simulation - Global Configuration
Defines simulation settings, thermal sensor thresholds, GPS coordinates, and aesthetic UI themes.
"""

import numpy as np

# Window & Display Dimensions
WINDOW_WIDTH = 1380
WINDOW_HEIGHT = 860
FPS = 60

# Layout Splits (Viewport vs Dashboard HUD)
MAP_WIDTH = 920
MAP_HEIGHT = 760
HUD_WIDTH = WINDOW_WIDTH - MAP_WIDTH
HUD_HEIGHT = WINDOW_HEIGHT

# Western Ghats GPS Geographic Boundaries (Nilgiri / Wayanad Sector)
GPS_LAT_MIN = 11.4000  # °N
GPS_LAT_MAX = 11.4500  # °N
GPS_LON_MIN = 76.6000  # °E
GPS_LON_MAX = 76.6800  # °E

# Temperature Thresholds (°C)
TEMP_AMBIENT_MIN = 24.0
TEMP_AMBIENT_MAX = 38.0
TEMP_HOTSPOT_THRESHOLD = 50.0      # Thermal anomaly threshold
TEMP_POTENTIAL_FIRE_MIN = 120.0    # Potential fire start
TEMP_CONFIRMED_FIRE_MIN = 280.0    # Confirmed wildfire baseline
TEMP_MAX = 800.0                   # Max wildfire intensity

# AI Fire Classifier Parameters
AI_CONFIDENCE_THRESHOLD = 0.75      # 75% confidence to confirm fire alert
AI_SAMPLING_RADIUS = 35.0          # Thermal pixels sampled in drone FOV
SMOKE_DENSITY_THRESHOLD = 0.35

# Drone Physics & Battery Parameters
DRONE_MAX_SPEED = 3.5
DRONE_CRUISE_SPEED = 2.2
DRONE_ACCELERATION = 0.15
DRONE_TURN_RATE = 0.08             # Radians per frame
DRONE_BATTERY_DRAIN_NORMAL = 0.025 # % per frame
DRONE_BATTERY_DRAIN_THERMAL = 0.04 # % when thermal imaging boost active
DRONE_BATTERY_RTB_THRESHOLD = 22.0 # % to trigger Return to Base
DRONE_BATTERY_RECHARGE_RATE = 0.4  # % per frame when docked

# Sensor Frustum
THERMAL_FOV_RADIUS = 110.0         # Pixel radius scanned on map
RAYCAST_NUM_RAYS = 12              # Rays for obstacle detection
RAYCAST_MAX_DIST = 90.0            # Max distance for obstacle raycast

# Color Palette (Dark Mode HUD & Rich Western Ghats Visuals)
COLOR_BG_DARK = (15, 23, 42)       # Slate 900
COLOR_PANEL_BG = (30, 41, 59)      # Slate 800
COLOR_PANEL_BORDER = (51, 65, 85)  # Slate 700
COLOR_TEXT_PRIMARY = (248, 250, 252)# Slate 50
COLOR_TEXT_MUTED = (148, 163, 184) # Slate 400
COLOR_ACCENT_BLUE = (56, 189, 248) # Sky 400
COLOR_ACCENT_GREEN = (74, 222, 128)# Emerald 400
COLOR_ACCENT_AMBER = (251, 191, 36)# Amber 400
COLOR_ACCENT_RED = (248, 113, 113) # Red 400
COLOR_BASE_DOCK = (34, 197, 94)    # Docking Station green

# Forest Map Colors
COLOR_WATER = (30, 78, 122)        # Kabini/Periyar River stream
COLOR_FOREST_CANOPY = (20, 54, 32) # Evergreen forest
COLOR_HILL_BASE = (42, 60, 48)     # Mountain hill elevation
COLOR_HILL_PEAK = (75, 92, 80)     # Mountain ridge

# Drone Colors per Unit
DRONE_COLORS = [
    (56, 189, 248),  # Drone Alpha (Sky Blue)
    (168, 85, 247),  # Drone Beta (Purple)
    (236, 72, 153)   # Drone Gamma (Pink)
]

# Control Station Alert Levels
SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_CRITICAL = "CRITICAL"
