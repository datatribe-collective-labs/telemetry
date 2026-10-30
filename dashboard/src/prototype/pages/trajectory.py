"""Trajectory page — Real (JPL Horizons) vs Synthetic (StateEngine) comparison."""

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.src.prototype.data.backend_api import SyncBackendAPI, get_api
from dashboard.src.prototype.pages._explain import explain

st.title("Trajectory — Real vs Synthetic")
st.caption("JPL Horizons ephemeris (ground truth) vs StateEngine physics model output")


# Sidebar
with st.sidebar:
    st.header("Time Range")
    # Window anchored to the Artemis II mission/replay window (synthetic + real data span Apr 1-10, 2026)
    default_end = datetime(2026, 4, 10, 23, 59, tzinfo=UTC)
    default_start = datetime(2026, 4, 1, 0, 0, tzinfo=UTC)
    
    date_range = st.date_input(
        "Date Range (UTC)",
        value=(default_start.date(), default_end.date()),
        key="traj_date_range"
    )
    
    t_start = st.time_input("Start time (UTC)", value=default_start.time(), key="trajectory_time_start")
    t_end = st.time_input("End time (UTC)", value=default_end.time(), key="trajectory_time_end")
    
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        date_from = datetime.combine(date_range[0], t_start, tzinfo=UTC)
        date_to = datetime.combine(date_range[1], t_end, tzinfo=UTC)
    else:
        date_from = default_start
        date_to = default_end
    
    limit = st.number_input("Max Points", 10, 5000, 500, 50, key="traj_limit")
    show_residuals = st.checkbox("Show Residuals (Real - Synthetic)", value=True)
    show_3d = st.checkbox("3D Trajectory", value=True)
    
    if st.button("Refresh", key="traj_refresh"):
        st.rerun()


api: SyncBackendAPI = get_api()


@st.cache_data(ttl=10)
def fetch_synthetic_state(date_from, date_to, limit):
    return api.get_synthetic_state(date_from=date_from, date_to=date_to, limit=limit)


@st.cache_data(ttl=10)
def fetch_real_orion(date_from, date_to, limit):
    return api.get_orion_ephemeris(date_from=date_from, date_to=date_to, limit=limit)


# Fetch data
syn_resp = fetch_synthetic_state(date_from, date_to, limit)
real_resp = fetch_real_orion(date_from, date_to, limit)

syn_items = syn_resp.items if syn_resp else []
real_items = real_resp.items if real_resp else []

if not syn_items and not real_items:
    st.warning("No data available for selected range.")
    st.stop()


# Convert to DataFrames
syn_df = pd.DataFrame([s.model_dump() for s in syn_items]) if syn_items else pd.DataFrame()
real_df = pd.DataFrame([r.model_dump() for r in real_items]) if real_items else pd.DataFrame()

# Real (JPL Horizons/orion_ephemeris) rows are keyed by `epoch`; synthetic rows by
# `timestamp_utc`. Normalize real onto the shared timestamp column used below.
if not real_df.empty and "epoch" in real_df.columns and "timestamp_utc" not in real_df.columns:
    real_df = real_df.rename(columns={"epoch": "timestamp_utc"})

for df in [syn_df, real_df]:
    if not df.empty and "timestamp_utc" in df.columns:
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
        df.sort_values("timestamp_utc", inplace=True)


# =========================================================================
# 3D TRAJECTORY
# =========================================================================
if show_3d and (not syn_df.empty or not real_df.empty):
    st.subheader("3D Geocentric Trajectory (EME2000)")
    explain("trajectory.3d")
    
    fig_3d = go.Figure()
    
    # Earth sphere
    r_earth = 6371.0
    u = np.linspace(0, 2 * np.pi, 25)
    v = np.linspace(0, np.pi, 25)
    x_earth = r_earth * np.outer(np.cos(u), np.sin(v))
    y_earth = r_earth * np.outer(np.sin(u), np.sin(v))
    z_earth = r_earth * np.outer(np.ones_like(u), np.cos(v))
    
    fig_3d.add_trace(go.Surface(
        x=x_earth, y=y_earth, z=z_earth,
        colorscale="Blues", showscale=False, opacity=0.3,
        name="Earth (R=6371 km)"
    ))
    
    # Real trajectory (JPL Horizons)
    if not real_df.empty and all(c in real_df.columns for c in ["x_km", "y_km", "z_km"]):
        fig_3d.add_trace(go.Scatter3d(
            x=real_df["x_km"], y=real_df["y_km"], z=real_df["z_km"],
            mode="lines+markers",
            marker={"size": 3, "color": real_df.get("speed_kms", 0), "colorscale": "Viridis", "colorbar": {"title": "Speed (km/s)", "len": 0.5}},
            line={"color": "#00D2FF", "width": 4},
            name="JPL Horizons (Real)",
            hovertext=real_df["timestamp_utc"].dt.strftime("%Y-%m-%d %H:%M UTC"),
            hovertemplate="<b>Real</b><br>%{hovertext}<br>X: %{x:,.0f} km<br>Y: %{y:,.0f} km<br>Z: %{z:,.0f} km<extra></extra>",
        ))
    
    # Synthetic trajectory (StateEngine)
    if not syn_df.empty and all(c in syn_df.columns for c in ["x_km", "y_km", "z_km"]):
        fig_3d.add_trace(go.Scatter3d(
            x=syn_df["x_km"], y=syn_df["y_km"], z=syn_df["z_km"],
            mode="lines+markers",
            marker={"size": 3, "color": syn_df.get("speed_kms", syn_df.get("vx_kms", 0)**2 + syn_df.get("vy_kms", 0)**2 + syn_df.get("vz_kms", 0)**2), "colorscale": "Plasma", "showscale": False},
            line={"color": "#FF6B6B", "width": 4, "dash": "dash"},
            name="StateEngine (Synthetic)",
            hovertext=syn_df["timestamp_utc"].dt.strftime("%Y-%m-%d %H:%M UTC"),
            hovertemplate="<b>Synthetic</b><br>%{hovertext}<br>X: %{x:,.0f} km<br>Y: %{y:,.0f} km<br>Z: %{z:,.0f} km<extra></extra>",
        ))
    
    fig_3d.update_layout(
        scene={
            "xaxis_title": "X (km)", "yaxis_title": "Y (km)", "zaxis_title": "Z (km)",
            "aspectmode": "data",
        },
        height=600,
        margin={"l": 0, "r": 0, "t": 30, "b": 0},
        legend={"orientation": "h", "y": -0.1}
    )
    st.plotly_chart(fig_3d, width="stretch")


# =========================================================================
# TIME SERIES COMPARISON
# =========================================================================
st.markdown("---")
st.subheader("Position & Velocity Comparison")
explain("trajectory.compare")

if not syn_df.empty and not real_df.empty:
    # Merge on nearest timestamp for residuals
    merged = pd.merge_asof(
        real_df.sort_values("timestamp_utc"),
        syn_df.sort_values("timestamp_utc"),
        on="timestamp_utc",
        direction="nearest",
        tolerance=pd.Timedelta("30s"),
        suffixes=("_real", "_syn")
    )
    
    if not merged.empty:
        # Compute residuals
        for coord in ["x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms"]:
            if f"{coord}_real" in merged.columns and f"{coord}_syn" in merged.columns:
                merged[f"{coord}_residual"] = merged[f"{coord}_real"] - merged[f"{coord}_syn"]
        
        if "range_km" in merged.columns and "earth_distance_km" in merged.columns:
            merged["range_residual_km"] = merged["range_km"] - merged["earth_distance_km"]
        
        if "speed_kms" in merged.columns:
            merged["speed_syn"] = np.sqrt(merged["vx_kms_syn"]**2 + merged["vy_kms_syn"]**2 + merged["vz_kms_syn"]**2)
            merged["speed_residual"] = merged["speed_kms"] - merged["speed_syn"]
    
    # Position plots
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("**Position (km)**")
        fig = go.Figure()
        for coord, color in [("x_km", "#00D2FF"), ("y_km", "#FF6B6B"), ("z_km", "#4ECDC4")]:
            if f"{coord}_real" in merged.columns:
                fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged[f"{coord}_real"], name=f"Real {coord.upper()}", line={"color": color, "width": 2}))
            if f"{coord}_syn" in merged.columns:
                fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged[f"{coord}_syn"], name=f"Syn {coord.upper()}", line={"color": color, "width": 2, "dash": "dash"}))
        fig.update_layout(height=350, margin={"l": 0, "r": 0, "t": 30, "b": 0}, legend={"orientation": "h", "y": -0.2})
        st.plotly_chart(fig, width="stretch")
        
        if show_residuals:
            st.markdown("**Position Residuals (Real - Synthetic)**")
            fig = go.Figure()
            for coord, color in [("x_km", "#00D2FF"), ("y_km", "#FF6B6B"), ("z_km", "#4ECDC4")]:
                if f"{coord}_residual" in merged.columns:
                    fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged[f"{coord}_residual"], name=f"Δ{coord.upper()}", line={"color": color, "width": 2}))
            fig.update_layout(height=200, margin={"l": 0, "r": 0, "t": 30, "b": 0}, yaxis_title="Residual (km)")
            st.plotly_chart(fig, width="stretch")
    
    with c2:
        st.markdown("**Velocity (km/s)**")
        fig = go.Figure()
        for coord, color in [("vx_kms", "#00D2FF"), ("vy_kms", "#FF6B6B"), ("vz_kms", "#4ECDC4")]:
            if f"{coord}_real" in merged.columns:
                fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged[f"{coord}_real"], name=f"Real {coord.upper()}", line={"color": color, "width": 2}))
            if f"{coord}_syn" in merged.columns:
                fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged[f"{coord}_syn"], name=f"Syn {coord.upper()}", line={"color": color, "width": 2, "dash": "dash"}))
        fig.update_layout(height=350, margin={"l": 0, "r": 0, "t": 30, "b": 0}, legend={"orientation": "h", "y": -0.2})
        st.plotly_chart(fig, width="stretch")
        
        if show_residuals:
            st.markdown("**Velocity Residuals (Real - Synthetic)**")
            fig = go.Figure()
            for coord, color in [("vx_kms", "#00D2FF"), ("vy_kms", "#FF6B6B"), ("vz_kms", "#4ECDC4")]:
                if f"{coord}_residual" in merged.columns:
                    fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged[f"{coord}_residual"], name=f"Δ{coord.upper()}", line={"color": color, "width": 2}))
            fig.update_layout(height=200, margin={"l": 0, "r": 0, "t": 30, "b": 0}, yaxis_title="Residual (km/s)")
            st.plotly_chart(fig, width="stretch")
    
    # Range & Speed
    st.markdown("**Range & Speed**")
    c3, c4 = st.columns(2)
    
    with c3:
        fig = go.Figure()
        if "range_km" in merged.columns:
            fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged["range_km"], name="Real Range", line={"color": "#00D2FF", "width": 2}))
        if "earth_distance_km" in merged.columns:
            fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged["earth_distance_km"], name="Syn Earth Dist", line={"color": "#FF6B6B", "width": 2, "dash": "dash"}))
        fig.update_layout(title="Range from Earth (km)", height=300, margin={"l": 0, "r": 0, "t": 30, "b": 0})
        st.plotly_chart(fig, width="stretch")
        
        if show_residuals and "range_residual_km" in merged.columns:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged["range_residual_km"], name="Range Residual", line={"color": "#EF553B", "width": 2}))
            fig.update_layout(title="Range Residual (km)", height=150, margin={"l": 0, "r": 0, "t": 30, "b": 0})
            st.plotly_chart(fig, width="stretch")
    
    with c4:
        fig = go.Figure()
        if "speed_kms" in merged.columns:
            fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged["speed_kms"], name="Real Speed", line={"color": "#00D2FF", "width": 2}))
        if "speed_syn" in merged.columns:
            fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged["speed_syn"], name="Syn Speed", line={"color": "#FF6B6B", "width": 2, "dash": "dash"}))
        fig.update_layout(title="Speed Magnitude (km/s)", height=300, margin={"l": 0, "r": 0, "t": 30, "b": 0})
        st.plotly_chart(fig, width="stretch")
        
        if show_residuals and "speed_residual" in merged.columns:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged["speed_residual"], name="Speed Residual", line={"color": "#EF553B", "width": 2}))
            fig.update_layout(title="Speed Residual (km/s)", height=150, margin={"l": 0, "r": 0, "t": 30, "b": 0})
            st.plotly_chart(fig, width="stretch")
    
    # Residual statistics
    if show_residuals:
        st.markdown("---")
        st.subheader("Residual Statistics (Real - Synthetic)")
        explain("trajectory.residuals")

        # Residual columns are all-NaN when no timestamps line up (real JPL arc starts
        # Apr 2 ~02:00 at 4-min cadence; synthetic replays from liftoff Apr 1 22:35 at
        # 1 Hz). Show an explanation instead of NaN metrics until the overlap exists.
        residual_cols = [f"{c}_residual" for c in ["x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms"] if f"{c}_residual" in merged.columns]
        matched = merged.dropna(subset=residual_cols) if residual_cols else merged.iloc[0:0]
        if matched.empty:
            syn_span = f"{syn_df['timestamp_utc'].min():%b %d %H:%M} – {syn_df['timestamp_utc'].max():%b %d %H:%M}Z"
            real_span = f"{real_df['timestamp_utc'].min():%b %d %H:%M} – {real_df['timestamp_utc'].max():%b %d %H:%M}Z"
            st.info(
                f"No overlapping timestamps yet — real JPL data spans **{real_span}**, "
                f"synthetic replay currently spans **{syn_span}**. Residuals appear once the "
                "simulation clock crosses the real-arc start (replay runs 1:1 from liftoff, "
                "so this fills in as it reaches Apr 2 ~02:00)."
            )
        else:
            stats_cols = st.columns(6)
            for i, (coord, label) in enumerate([("x_km", "X"), ("y_km", "Y"), ("z_km", "Z"), ("vx_kms", "VX"), ("vy_kms", "VY"), ("vz_kms", "VZ")]):
                col = f"{coord}_residual"
                if col in merged.columns:
                    vals = merged[col].dropna()
                    with stats_cols[i]:
                        st.metric(f"Δ{label} Mean", f"{vals.mean():.3f}")
                        st.caption(f"Std: {vals.std():.3f} | Max: {vals.max():.3f}")

elif not syn_df.empty:
    st.info("Only synthetic data available. Run JPL Horizons ingestion for real comparison.")
    # Show synthetic only
    c1, c2 = st.columns(2)
    with c1:
        fig = px.line(syn_df, x="timestamp_utc", y=["x_km", "y_km", "z_km"], title="Synthetic Position")
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig = px.line(syn_df, x="timestamp_utc", y=["vx_kms", "vy_kms", "vz_kms"], title="Synthetic Velocity")
        st.plotly_chart(fig, width="stretch")

elif not real_df.empty:
    st.info("Only real (JPL) data available. Run physics models for synthetic comparison.")
    c1, c2 = st.columns(2)
    with c1:
        fig = px.line(real_df, x="timestamp_utc", y=["x_km", "y_km", "z_km"], title="Real Position (JPL)")
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig = px.line(real_df, x="timestamp_utc", y=["vx_kms", "vy_kms", "vz_kms"], title="Real Velocity (JPL)")
        st.plotly_chart(fig, width="stretch")


# =========================================================================
# SOLAR GEOMETRY & ECLIPSE
# =========================================================================
if not syn_df.empty:
    st.markdown("---")
    st.subheader("Solar Geometry & Eclipse (Synthetic)")
    explain("trajectory.solar")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        if "solar_flux_w_m2" in syn_df.columns:
            fig = px.line(syn_df, x="timestamp_utc", y="solar_flux_w_m2", title="Solar Flux (W/m²)")
            st.plotly_chart(fig, width="stretch")
    with c2:
        if "solar_incidence_angle_deg" in syn_df.columns:
            fig = px.line(syn_df, x="timestamp_utc", y="solar_incidence_angle_deg", title="Solar Incidence Angle (°)")
            st.plotly_chart(fig, width="stretch")
    with c3:
        if "eclipse_state" in syn_df.columns:
            eclipse_map = {"SUNLIT": 0, "PENUMBRA": 0.5, "UMBRA": 1}
            syn_df["eclipse_numeric"] = syn_df["eclipse_state"].map(eclipse_map)
            fig = px.line(syn_df, x="timestamp_utc", y="eclipse_numeric", title="Eclipse State")
            fig.update_yaxes(tickvals=[0, 0.5, 1], ticktext=["SUNLIT", "PENUMBRA", "UMBRA"])
            st.plotly_chart(fig, width="stretch")