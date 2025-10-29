import streamlit as st
import folium
import pandas as pd
import adif_io
import maidenhead
import re

from io import StringIO, BytesIO
from math import radians, degrees, atan2, sin, cos
from streamlit_folium import folium_static
from geopy.distance import great_circle
from geopy import Point

# Streamlit page configuration
st.set_page_config(page_title="QSO Mapper", layout="wide")
st.title("🌍 EA1RFI's QSO World Mapper")

band_colors = {
    "160M": "darkred",
    "80M": "red",
    "60M": "orange",
    "40M": "darkorange",
    "30M": "gold",
    "20M": "green",
    "17M": "darkgreen",
    "15M": "blue",
    "12M": "darkblue",
    "10M": "purple",
    "6M": "magenta",
    "2M": "gray",
}

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

def color_for_band(band):
    """
    Assigns colour to band
    """
    if not isinstance(band, str):
        return "black"
    band_upper = band.strip().upper()
    return band_colors.get(band_upper, "black")

def create_map(qsos, my_grid, my_call):
    """
    Generates a Folium map with QSOs.
    """
    my_lat, my_lon = maidenhead.to_location(my_grid)

    m = folium.Map(location=[my_lat, my_lon], zoom_start=2, tiles="CartoDB positron")

    # Mi QTH
    folium.Marker(
        [my_lat, my_lon],
        tooltip=f"My QTH: {my_call} ({my_grid})",
        icon=folium.Icon(color="red", icon="home")
    ).add_to(m)

    for _, row in qsos.iterrows():
        call = row.get("CALL", "N/A")
        grid = row.get("GRIDSQUARE", "")
        band = str(row.get("BAND", ""))
        freq = str(row.get("FREQ", ""))
        mode = row.get("MODE", "")
        color = color_for_band(band)

        tooltip = f"{call}<br>Band: {band}<br>Freq: {freq} MHz<br>Mode: {mode}<br>Grid: {grid}"

        folium.CircleMarker(
            [row["lat"], row["lon"]],
            radius=5,
            color=color,
            fill=True,
            fill_opacity=0.8,
            tooltip=tooltip
        ).add_to(m)

        points = great_circle_path(my_lat, my_lon, row["lat"], row["lon"], n_points=60)

        folium.PolyLine(
            locations=points,
            color=color,
            weight=1,
            opacity=0.7
        ).add_to(m)

    # Leyenda
    legend_html = """
    <div style="
        position: fixed;
        bottom: 30px;
        left: 30px;
        width: 80px;
        background-color: white;
        border:2px solid grey;
        z-index:9999;
        font-size:14px;
        border-radius:10px;
        padding:10px;
        box-shadow:2px 2px 4px rgba(0,0,0,0.3);
    ">
    <b>Bands</b><br>
    """
    for band, color in band_colors.items():
        legend_html += f"<div style='display:flex;align-items:center;'><div style='width:15px;height:15px;background:{color};margin-right:5px;border-radius:3px;'></div>{band}</div>"
    legend_html += "</div>"
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


# Streamlit interface

st.sidebar.header("Configuration")

my_call = st.sidebar.text_input("Your Callsign:", "EA1RFI")
my_grid = st.sidebar.text_input("Your locator (grid):", "IN52PE")

uploaded_file = st.file_uploader("📂 Upload your ADIF file (.adi)", type=["adi", "adif"])

if uploaded_file:
    adif_content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
    adif_data, _ = adif_io.read_from_string(adif_content)
    qsos = pd.DataFrame(adif_data)

    st.success(f"✅ {len(qsos)} QSOs loaded")

    # Obtener coordenadas
    qsos["lat"], qsos["lon"] = zip(*qsos.apply(get_lat_lon, axis=1))
    qsos = qsos.dropna(subset=["lat", "lon","GRIDSQUARE"])

    if qsos.empty:
        st.warning("⚠️ No valid coordinates were found")
    else:
        mapa = create_map(qsos, my_grid, my_call)

        # Mostrar mapa
        st_data = folium_static(mapa, width=1200, height=700)

        # Botón de descarga
        html_buffer = BytesIO()
        mapa.save(html_buffer, close_file=False)
        html_data = html_buffer.getvalue().decode()

        st.download_button(
            label="💾 Download HTML map file",
            data=html_data,
            file_name="map_qsos.html",
            mime="text/html"
        )
else:
    st.info("👆 Upload your ADIF file to generate the map")

