import streamlit as st
import folium
import maidenhead

from io import StringIO, BytesIO
from streamlit_folium import st_folium
from geopy import Point
from core.db import log_upload
from core.adif_utils import load_adif
from core.geo_utils import get_lat_lon, haversine, great_circle_path, calculate_azimuth
from core.stats_plots import plot_qsos_by_band, plot_polar_char_azimuth

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

tab_map, tab_stats = st.tabs(["🗺️ QSO Map", "📊 QSO Stats"])

uploaded_file = st.file_uploader("📂 Upload your ADIF file (.adi)", type=["adi", "adif"])

if uploaded_file:

    qsos = load_adif(uploaded_file.getvalue())

    st.success(f"✅ {len(qsos)} QSOs loaded")

    headers = st.context.headers if hasattr(st, "context") else {}
    log_upload(
        callsign=my_call,
        filename=uploaded_file.name,
        qso_count=len(qsos),
        request_headers=headers
    )

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

