import re
import numpy as np
import maidenhead
import pandas as pd

from math import radians, degrees, atan2, sin, cos
from geopy.distance import great_circle, geodesic

def adif_coord_to_decimal(coord):
    """
    Converts ADIF coordinates such as 'N42 52.560' or 'W008 32.700' to decimal.
    """
    if not isinstance(coord, str) or not re.match(r'^[NSWE]', coord.strip()):
        return None

    hemi = coord[0].upper()
    coord = coord[1:].strip()
    try:
        deg, mins = coord.split(" ")
        deg = float(deg)
        mins = float(mins)
        decimal = deg + mins / 60.0
        if hemi in ['S', 'W']:
            decimal = -decimal
        return decimal
    except Exception:
        return None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

def get_lat_lon(row):
    """
    Obtains coordinates from the the grid or lat/lon fields in the QSO.
    """
    grid = row.get("GRIDSQUARE") or row.get("MY_GRIDSQUARE")
    if isinstance(grid, str):
        try:
            return maidenhead.to_location(grid)
        except Exception:
            pass

    lat = row.get("LAT")
    lon = row.get("LON")
    if isinstance(lat, str) and isinstance(lon, str):
        lat_dec = adif_coord_to_decimal(lat)
        lon_dec = adif_coord_to_decimal(lon)
        if lat_dec is not None and lon_dec is not None:
            return lat_dec, lon_dec

    return None, None

def great_circle_path(lat1, lon1, lat2, lon2, n_points=50):
    """
    Calculates intermediate points through the great circle between two coordinates to paint it in the map.
    """
    coords = []
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Distancia angular
    d = 2 * atan2(((sin((lat2 - lat1) / 2))**2 + cos(lat1) * cos(lat2) * (sin((lon2 - lon1) / 2))**2)**0.5,
                  (1 - ((sin((lat2 - lat1) / 2))**2 + cos(lat1) * cos(lat2) * (sin((lon2 - lon1) / 2))**2)**0.5)**0.5)

    for i in range(n_points + 1):
        f = i / n_points
        A = sin((1 - f) * d) / sin(d)
        B = sin(f * d) / sin(d)
        x = A * cos(lat1) * cos(lon1) + B * cos(lat2) * cos(lon2)
        y = A * cos(lat1) * sin(lon1) + B * cos(lat2) * sin(lon2)
        z = A * sin(lat1) + B * sin(lat2)
        lat = atan2(z, (x**2 + y**2)**0.5)
        lon = atan2(y, x)
        coords.append((degrees(lat), (degrees(lon) + 540) % 360 - 180))
    return coords
    
def calculate_azimuth(my_grid, row):
    """
    Calculates azimuth (bearing) in degrees from QTH to QSO
    """
    if pd.isna(row["lat"]) or pd.isna(row["lon"]):
        return None

    lat1, lon1 = maidenhead.to_location(my_grid)
    lat2, lon2 = row["lat"], row["lon"]

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlon = lon2 - lon1

    x = sin(dlon) * cos(lat2)
    y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)

    bearing = (degrees(atan2(x, y)) + 360) % 360
    return bearing