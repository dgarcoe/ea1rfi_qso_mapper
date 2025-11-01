import streamlit as st
import folium
import pandas as pd
import adif_io
import maidenhead
import tempfile
import re

from io import StringIO, BytesIO
from math import radians, degrees, atan2, sin, cos
from streamlit_folium import st_folium
from geopy.distance import great_circle, geodesic
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

def clean_adif_header(adif_str: str) -> str:
    """
    Eliminates the header
    """
    match = re.search(r"<EOH\s*>", adif_str, flags=re.IGNORECASE)
    if not match:
        # si no hay <EOH>, devuelve el contenido tal cual
        return adif_str
    # Devuelve el contenido a partir del primer carácter después de <EOH>
    return adif_str[match.end():].lstrip()

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

def calculate_distances(my_grid, row):
    """
    Calculates distances from your grid to each QSO
    """
    qth_coords = maidenhead.to_location(my_grid)

    qso_coords = (row["lat"], row["lon"])

    if pd.isna(row["lat"]):
        return
    else:
        return geodesic(qth_coords, qso_coords).km

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

    m = folium.Map(location=[my_lat, my_lon], zoom_start=2, tiles="Esri.WorldStreetMap")

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
        freq = str(row.get("FREQ", "")).rstrip("0")
        dist = '{0:.2f}'.format(row.get("DISTANCE", ""))
        mode = row.get("MODE", "")
        color = color_for_band(band)

        tooltip = f"<b>{call}</b><br>Band: {band}<br>Freq: {freq} MHz<br>Mode: {mode}<br>Grid: {grid}<br>Distance: {dist} Km"

        folium.CircleMarker(
            [row["lat"], row["lon"]],
            radius=circle_size,
            color=color,
            fill=True,
            fill_opacity=0.8,
            tooltip=tooltip
        ).add_to(m)

        if show_gc:
            points = great_circle_path(my_lat, my_lon, row["lat"], row["lon"], n_points=20)

            folium.PolyLine(
                locations=points,
                color=color,
                weight=1,
                opacity=0.7
            ).add_to(m)

    # Map legend
    legend_html = """
    <div style="
        position: fixed;
        bottom: 30px;
        left: 30px;
        width: 80px;
        background-color: black;
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

st.sidebar.header("Your Data")

my_call = st.sidebar.text_input("Your Callsign:", "EA1RFI")
my_grid = st.sidebar.text_input("Your locator (grid):", "IN52PE")

st.sidebar.header("⚙️ Filters")
circle_size = st.sidebar.slider("Size of QSO markers", 1, 6, 4)
show_gc = st.sidebar.checkbox("Show Great Circle lines", value=True)

uploaded_file = st.file_uploader("📂 Upload your ADIF file (.adi)", type=["adi", "adif"])

if uploaded_file:

    adif_content = uploaded_file.getvalue().decode(encoding="ISO-8859-15",errors="ignore")
    # The adif_io library has issues when logs have duplicated fields in the header so we delete it before processing it
    adif_content_clean = clean_adif_header(adif_content)
    adif_data, _ = adif_io.read_from_string(adif_content_clean)
    qsos = pd.DataFrame(adif_data)

    st.success(f"✅ {len(qsos)} QSOs loaded")

    # Obtain coordinates
    qsos["lat"], qsos["lon"] = zip(*qsos.apply(get_lat_lon, axis=1))
    qsos["DISTANCE"] = qsos.apply(lambda r: calculate_distances(my_grid,r), axis=1)
    qsos = qsos.dropna(subset=["lat", "lon","GRIDSQUARE"])

    if qsos.empty:
        st.warning("⚠️ No valid coordinates were found")
    else:
        mapa = create_map(qsos, my_grid, my_call)

        # Show map
        st_data = st_folium(mapa, width=1200, height=700)

        # Download button
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

