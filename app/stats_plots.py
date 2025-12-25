import plotly.express as px
import streamlit as st

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