import streamlit as st
import folium
import pandas as pd
import adif_io
import maidenhead
import tempfile
import re
import plotly.express as px
import numpy as np



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

@st.cache_data(show_spinner="Parsing ADIF…")
def load_adif(file_bytes):

    adif_content = file_bytes.decode(encoding="ISO-8859-15", errors="ignore")
    adif_content_clean = clean_adif_header(adif_content)
    adif_data, _ = adif_io.read_from_string(adif_content_clean)

    return pd.DataFrame(adif_data)

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

def plot_qsos_by_band(qsos):
    """
    Plots QSOs by band
    """
    band_counts = (
        qsos["BAND"]
            .value_counts()
            .reset_index()
            .rename(columns={"index": "BAND", "count": "QSOS"})
        )

    fig_band = px.bar(
        band_counts,
        x="BAND",
        y="QSOS",
        title="QSOs by band",
        labels={"BAND": "Band", "QSOS": "QSOs"}
    )
        
    st.plotly_chart(fig_band, width='stretch')

def plot_polar_char_azimuth(qsos):
    """
    Plots polar chart using azimuth
    """
    azimuth_counts = (
        qsos["AZ_BIN"]
        .value_counts()
        .sort_index()
        .reset_index()
        .rename(columns={"index": "AZIMUTH", "count": "QSOS"})
    )


    fig_az = px.bar_polar(
        azimuth_counts,
        r="QSOS",
        theta="AZ_BIN",
        title="QSOs by bearing",
        labels={"QSOS": "QSOs", "AZIMUTH": "Bearing (°)"},
    )

    fig_az.update_layout(
        polar=dict(
            angularaxis=dict(
                direction="clockwise",
                rotation=90
            )
        )
    )

    st.plotly_chart(fig_az, width='stretch')


# Streamlit interface

st.sidebar.header("Your Data")

my_call = st.sidebar.text_input("Your Callsign:", "EA1RFI")
my_grid = st.sidebar.text_input("Your locator (grid):", "IN52PE")

st.sidebar.header("⚙️ Filters")
circle_size = st.sidebar.slider("Size of QSO markers", 1, 6, 4)
show_gc = st.sidebar.checkbox("Show Great Circle lines", value=True)

tab_map, tab_stats = st.tabs(["🗺️ QSO Map", "📊 QSO Stats"])

uploaded_file = st.file_uploader("📂 Upload your ADIF file (.adi)", type=["adi", "adif"])

if uploaded_file:

    qsos = load_adif(uploaded_file.getvalue())

    st.success(f"✅ {len(qsos)} QSOs loaded")

    # Obtain coordinates
    qsos["lat"], qsos["lon"] = zip(*qsos.apply(get_lat_lon, axis=1))
    my_lat, my_lon = maidenhead.to_location(my_grid)
    qsos["DISTANCE"] = haversine(my_lat, my_lon, qsos["lat"], qsos["lon"])
    qsos = qsos.dropna(subset=["lat", "lon","GRIDSQUARE"])

    qsos["AZIMUTH"] = qsos.apply(lambda r: calculate_azimuth(my_grid, r), axis=1)
    qsos = qsos.dropna(subset=["AZIMUTH"])
    qsos["AZ_BIN"] = (qsos["AZIMUTH"] // 10) * 10


    if qsos.empty:
        st.warning("⚠️ No valid coordinates were found")
    else:
        
        with tab_map:
            st.subheader("QSO World Map")

            map = create_map(qsos, my_grid, my_call)

            # Show map
            st_data = st_folium(map, width=1200, height=700)

            # Download button
            html_buffer = BytesIO()
            map.save(html_buffer, close_file=False)
            html_data = html_buffer.getvalue().decode()

            st.download_button(
                label="💾 Download HTML map file",
                data=html_data,
                file_name="map_qsos.html",
                mime="text/html"
            )

        with tab_stats:
            st.subheader("QSO Stats")
            
             # ===== Filas de gráficos =====
            col_left, col_right = st.columns(2)

            with col_left:
                plot_qsos_by_band(qsos)

            with col_right:
                plot_polar_char_azimuth(qsos)


else:
    st.info("👆 Upload your ADIF file to generate the map")

