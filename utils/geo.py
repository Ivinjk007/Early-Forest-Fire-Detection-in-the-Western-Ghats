"""
Geographic Coordinate Utility for Western Ghats Simulation.
Translates 2D map pixel coordinates (X, Y) to real-world Latitude and Longitude.
"""

from config import MAP_WIDTH, MAP_HEIGHT, GPS_LAT_MIN, GPS_LAT_MAX, GPS_LON_MIN, GPS_LON_MAX

def pixel_to_gps(x: float, y: float) -> tuple[float, float]:
    """
    Converts map pixel coordinates (x, y) to (latitude, longitude) in Western Ghats.
    x: 0 to MAP_WIDTH -> Longitude GPS_LON_MIN to GPS_LON_MAX
    y: 0 to MAP_HEIGHT -> Latitude GPS_LAT_MAX to GPS_LAT_MIN (Y inverted for screen)
    """
    # Normalize coordinates
    norm_x = max(0.0, min(1.0, x / MAP_WIDTH))
    norm_y = max(0.0, min(1.0, y / MAP_HEIGHT))
    
    # Calculate GPS
    longitude = GPS_LON_MIN + norm_x * (GPS_LON_MAX - GPS_LON_MIN)
    latitude = GPS_LAT_MAX - norm_y * (GPS_LAT_MAX - GPS_LAT_MIN)
    
    return round(latitude, 5), round(longitude, 5)

def format_gps(lat: float, lon: float) -> str:
    """Formats latitude and longitude into human-readable string."""
    lat_dir = 'N' if lat >= 0 else 'S'
    lon_dir = 'E' if lon >= 0 else 'W'
    return f"{abs(lat):.4f}°{lat_dir}, {abs(lon):.4f}°{lon_dir}"

def distance_pixels(pos1: tuple[float, float], pos2: tuple[float, float]) -> float:
    """Euclidean distance between two pixel positions."""
    return ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2) ** 0.5
