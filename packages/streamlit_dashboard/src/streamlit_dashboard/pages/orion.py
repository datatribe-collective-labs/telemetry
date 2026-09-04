"""Artemis II Orion Spacecraft Telemetry & Ephemeris page.

Reads the `orion_ephemeris` table populated by `pipelines.ingest.jpl_orion`
and overlays Moon ephemeris data and 3D Earth globe mesh.
"""

from datetime import date, datetime, time

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from astroquery.jplhorizons import Horizons

from streamlit_dashboard.data.engine import get_engine
from streamlit_dashboard.data.orion import load_orion_ephemeris

MU_EARTH = 398600.4418  # Earth gravitational parameter in km^3 / s^2


@st.cache_data(ttl=3600)
def fetch_moon_ephemeris(start_dt: datetime, stop_dt: datetime) -> pd.DataFrame:
    """Fetch Moon (id=301) vectors directly from JPL Horizons for visual overlay."""
    try:
        start_str = start_dt.strftime("%Y-%m-%d %H:%M")
        stop_str = stop_dt.strftime("%Y-%m-%d %H:%M")
        obj = Horizons(
            id="301",
            location="500@399",
            epochs={"start": start_str, "stop": stop_str, "step": "1h"},
        )
        vec = obj.vectors().to_pandas()
        return pd.DataFrame(
            {
                "epoch": pd.to_datetime(
                    vec["datetime_str"].str.replace("A.D.", "").str.strip()
                ),
                "x_km": vec["x"] * 149597870.7,
                "y_km": vec["y"] * 149597870.7,
                "z_km": vec["z"] * 149597870.7,
                "range_km": vec["range"] * 149597870.7,
            }
        )
    except Exception:
        return pd.DataFrame()


st.title("Artemis II Orion - JPL Horizons Telemetry")
st.caption(
    "Real-time position & velocity state vectors for NASA Artemis II Orion Spacecraft (-1024), "
    "sourced from JPL Horizons."
)

with st.sidebar:
    st.header("Ephemeris Filters")
    default_start = date(2026, 4, 2)
    default_stop = date(2026, 4, 10)



    date_range = st.date_input(
        "Date Range (UTC)",
        value=(default_start, default_stop),
    )
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        date_from = datetime.combine(date_range[0], time.min)
        date_to = datetime.combine(date_range[1], time.max)
    else:
        date_from = datetime.combine(default_start, time.min)
        date_to = datetime.combine(default_stop, time.max)

engine = get_engine()
df = load_orion_ephemeris(engine, date_from, date_to)

if df.empty:
    st.warning("No Orion telemetry records found in TimescaleDB for the selected date range.")
    st.info("Run `uv run --package pipelines python -m pipelines.ingest.jpl_orion` to ingest Orion ephemeris data.")
else:
    # Compute Specific Orbital Energy: epsilon = v^2 / 2 - mu / r
    if "speed_kms" in df.columns and "range_km" in df.columns:
        df["specific_energy"] = (df["speed_kms"] ** 2 / 2.0) - (MU_EARTH / df["range_km"])

    # High-level Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Telemetry Points", len(df))
    max_range = df["range_km"].max()
    col2.metric("Max Range from Earth", f"{max_range:,.0f} km" if pd.notna(max_range) else "N/A")
    max_speed = df["speed_kms"].max()
    col3.metric("Peak Speed", f"{max_speed:.3f} km/s" if pd.notna(max_speed) else "N/A")
    min_energy = df["specific_energy"].min() if "specific_energy" in df.columns else None
    col4.metric("Min Orbital Energy", f"{min_energy:.2f} km²/s²" if min_energy is not None else "N/A")

    st.markdown("---")

    # 3D Orbit Trajectory Visualization with Earth Mesh & Moon Overlay
    st.subheader("Enhanced 3D Geocentric Trajectory (Orion & Moon)")
    fig_3d = go.Figure()

    # 3D Earth Surface Mesh (Radius ~ 6371 km)
    r_earth = 6371.0
    u = np.linspace(0, 2 * np.pi, 30)
    v = np.linspace(0, np.pi, 30)
    x_earth = r_earth * np.outer(np.cos(u), np.sin(v))
    y_earth = r_earth * np.outer(np.sin(u), np.sin(v))
    z_earth = r_earth * np.outer(np.ones(np.size(u)), np.cos(v))

    fig_3d.add_trace(
        go.Surface(
            x=x_earth,
            y=y_earth,
            z=z_earth,
            colorscale="Blues",
            showscale=False,
            opacity=0.8,
            name="Earth Globe (R=6371km)",
        )
    )

    # Orion Path
    fig_3d.add_trace(
        go.Scatter3d(
            x=df["x_km"],
            y=df["y_km"],
            z=df["z_km"],
            mode="lines+markers",
            marker=dict(
                size=3,
                color=df["speed_kms"],
                colorscale="Plasma",
                colorbar=dict(title="Speed (km/s)", len=0.7),
                showscale=True,
            ),
            line=dict(color="#00D2FF", width=4),
            name="Orion Path (-1024)",
            hovertext=df["epoch"].dt.strftime("%Y-%m-%d %H:%M UTC"),
            hovertemplate="<b>Orion</b><br>Epoch: %{hovertext}<br>X: %{x:,.0f} km<br>Y: %{y:,.0f} km<br>Z: %{z:,.0f} km<extra></extra>",
        )
    )

    # Fetch and overlay Moon orbit
    df_moon = fetch_moon_ephemeris(date_from, date_to)
    if not df_moon.empty:
        fig_3d.add_trace(
            go.Scatter3d(
                x=df_moon["x_km"],
                y=df_moon["y_km"],
                z=df_moon["z_km"],
                mode="lines",
                line=dict(color="gray", width=3, dash="dash"),
                name="Moon Orbit (301)",
                hovertext=df_moon["epoch"].dt.strftime("%Y-%m-%d %H:%M UTC"),
                hovertemplate="<b>Moon</b><br>Epoch: %{hovertext}<br>Range: %{x:,.0f} km<extra></extra>",
            )
        )
        fig_3d.add_trace(
            go.Scatter3d(
                x=[df_moon["x_km"].iloc[-1]],
                y=[df_moon["y_km"].iloc[-1]],
                z=[df_moon["z_km"].iloc[-1]],
                mode="markers+text",
                marker=dict(size=8, color="lightgray"),
                name="Moon Position",
                text=["Moon"],
                textposition="top center",
            )
        )

    fig_3d.update_layout(
        scene=dict(
            xaxis_title="X (km)",
            yaxis_title="Y (km)",
            zaxis_title="Z (km)",
            aspectmode="data",
        ),
        height=700,
        margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(fig_3d, use_container_width=True)

    # Line Charts: Range, Speed & Specific Energy Profiles
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Geocentric Distance (Range)")
        fig_range = px.line(
            df,
            x="epoch",
            y="range_km",
            labels={"epoch": "Time (UTC)", "range_km": "Range (km)"},
            title="Orion Range from Earth over Time",
        )
        fig_range.update_traces(line_color="#4B9CD3", line_width=2.5)
        fig_range.update_layout(margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_range, use_container_width=True)

    with chart_col2:
        st.subheader("Orbital Speed Profile")
        fig_speed = px.line(
            df,
            x="epoch",
            y="speed_kms",
            labels={"epoch": "Time (UTC)", "speed_kms": "Speed (km/s)"},
            title="Orion Speed Magnitude over Time",
        )
        fig_speed.update_traces(line_color="#FF4B4B", line_width=2.5)
        fig_speed.update_layout(margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_speed, use_container_width=True)

    # Specific Orbital Energy Chart
    st.subheader("Specific Orbital Energy Profile (epsilon)")
    if "specific_energy" in df.columns:
        fig_energy = px.line(
            df,
            x="epoch",
            y="specific_energy",
            labels={
                "epoch": "Time (UTC)",
                "specific_energy": "Specific Energy (km²/s²)",
            },
            title="Orion Specific Orbital Energy over Time",
        )
        fig_energy.add_hline(
            y=0,
            line_dash="dash",
            line_color="red",
            annotation_text="Parabolic Escape Threshold (epsilon = 0)",
        )
        fig_energy.update_traces(line_color="#00CC96", line_width=2.5)
        fig_energy.update_layout(height=400, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_energy, use_container_width=True)

    # Telemetry Data Table
    st.subheader("Raw Vector Telemetry Records")
    display_cols = {
        "epoch": "Epoch (UTC)",
        "x_km": "X (km)",
        "y_km": "Y (km)",
        "z_km": "Z (km)",
        "vx_kms": "VX (km/s)",
        "vy_kms": "VY (km/s)",
        "vz_kms": "VZ (km/s)",
        "speed_kms": "Speed (km/s)",
        "range_km": "Range (km)",
        "specific_energy": "Energy (km²/s²)",
    }
    present_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(
        df[present_cols].rename(columns=display_cols),
        use_container_width=True,
        hide_index=True,
    )

