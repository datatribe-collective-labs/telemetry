"""DSN Coverage page — Real-time DSN visibility and geometry."""

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.src.prototype.data.backend_api import SyncBackendAPI, get_api
from dashboard.src.prototype.pages._explain import explain

st.title("DSN Coverage")
st.caption("Deep Space Network visibility for Artemis II Orion — Real JPL Horizons observer data")


# Sidebar
with st.sidebar:
    st.header("Time Range")
    # Window anchored to the Artemis II mission/replay window (synthetic + real data span Apr 1-10, 2026)
    default_end = datetime(2026, 4, 10, 23, 59, tzinfo=UTC)
    default_start = datetime(2026, 4, 1, 0, 0, tzinfo=UTC)
    
    date_range = st.date_input(
        "Date Range (UTC)",
        value=(default_start.date(), default_end.date()),
        key="dsn_date_range"
    )
    
    t_start = st.time_input("Start time (UTC)", value=default_start.time(), key="dsn_coverage_time_start")
    t_end = st.time_input("End time (UTC)", value=default_end.time(), key="dsn_coverage_time_end")
    
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        date_from = datetime.combine(date_range[0], t_start, tzinfo=UTC)
        date_to = datetime.combine(date_range[1], t_end, tzinfo=UTC)
    else:
        date_from = default_start
        date_to = default_end
    
    limit = st.number_input("Max Points", 10, 1000, 500, 100, key="dsn_limit")  # backend caps at 1000
    complex_filter = st.multiselect("Complex", ["Goldstone", "Madrid", "Canberra"], default=["Goldstone", "Madrid", "Canberra"])
    site_filter = st.multiselect("Site", ["DSS-14", "DSS-15", "DSS-24", "DSS-25", "DSS-26", "DSS-34", "DSS-35", "DSS-36", "DSS-43", "DSS-45", "DSS-53", "DSS-54", "DSS-55", "DSS-56"])
    visible_only = st.checkbox("Visible Only (elev ≥ 10°)", value=True)
    
    if st.button("Refresh", key="dsn_refresh"):
        st.rerun()


api: SyncBackendAPI = get_api()


@st.cache_data(ttl=30)
def fetch_dsn(date_from, date_to, limit):
    return api.get_dsn_geometry(date_from=date_from, date_to=date_to, limit=limit)


resp = fetch_dsn(date_from, date_to, limit)
items = resp.items if resp else []

if not items:
    st.warning("No DSN geometry data available for selected range.")
    st.stop()


df = pd.DataFrame([item.model_dump() for item in items])
df = df.sort_values("epoch")

# Apply filters
if complex_filter:
    df = df[df["complex"].isin(complex_filter)]
if site_filter:
    df = df[df["site"].isin(site_filter)]
if visible_only and "visible" in df.columns:
    df = df[df["visible"] == True]


# =========================================================================
# CURRENT VISIBILITY STATUS
# =========================================================================
st.subheader("Current DSN Visibility")
explain("dsn.current")

if "visible" in df.columns:
    latest = df.sort_values("epoch").groupby("site").last().reset_index()
    
    # Group by complex
    for complex_name in ["Goldstone", "Madrid", "Canberra"]:
        complex_df = latest[latest["complex"] == complex_name]
        if complex_df.empty:
            continue
        
        st.markdown(f"### {complex_name} Complex")
        cols = st.columns(len(complex_df))
        for i, (_, row) in enumerate(complex_df.iterrows()):
            with cols[i]:
                site = row.get("site", "?")
                visible = row.get("visible", False)
                elev = row.get("elevation_deg")
                az = row.get("azimuth_deg")
                rng = row.get("range_km")
                lt = row.get("light_time_s")
                
                if visible:
                    st.success(f"🟢 {site} — VISIBLE")
                else:
                    st.error(f"🔴 {site} — BELOW HORIZON")
                
                st.caption(f"Elev: {elev:.1f}°" if pd.notna(elev) else "Elev: N/A")
                st.caption(f"Az: {az:.1f}°" if pd.notna(az) else "Az: N/A")
                st.caption(f"Range: {rng:,.0f} km" if pd.notna(rng) else "Range: N/A")
                st.caption(f"Light Time: {lt:.1f} s" if pd.notna(lt) else "LT: N/A")


# =========================================================================
# ELEVATION TIMELINES
# =========================================================================
st.markdown("---")
st.subheader("Elevation Angles Over Time")
explain("dsn.elevation")

if "elevation_deg" in df.columns and "site" in df.columns:
    fig = go.Figure()
    
    complex_colors = {
        "Goldstone": "#00D2FF",
        "Madrid": "#FF6B6B",
        "Canberra": "#4ECDC4"
    }
    
    for site in df["site"].unique():
        site_df = df[df["site"] == site].sort_values("epoch")
        complex_name = site_df["complex"].iloc[0] if "complex" in site_df.columns else "Unknown"
        color = complex_colors.get(complex_name, "#888888")
        
        fig.add_trace(go.Scatter(
            x=site_df["epoch"], y=site_df["elevation_deg"],
            name=f"{site} ({complex_name})", mode="lines", line={"color": color, "width": 1.5},
            hovertemplate="<b>%{fullData.name}</b><br>Time: %{x}<br>Elev: %{y:.1f}°<extra></extra>"
        ))
    
    fig.add_hline(y=10, line_dash="dash", line_color="red", annotation_text="10° Elevation Mask (Operational Minimum)")
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    
    fig.update_layout(
        title="DSN Site Elevation Angles",
        yaxis_title="Elevation (°)",
        height=500,
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
        legend={"orientation": "h", "y": -0.15}
    )
    st.plotly_chart(fig, width="stretch")


# =========================================================================
# POLAR VISIBILITY PLOTS (per complex)
# =========================================================================
st.markdown("---")
st.subheader("Polar Visibility Plots (Azimuth vs Elevation)")
explain("dsn.polar")

for complex_name in ["Goldstone", "Madrid", "Canberra"]:
    complex_df = df[df["complex"] == complex_name]
    if complex_df.empty:
        continue
    
    st.markdown(f"### {complex_name}")
    
    fig = go.Figure()
    
    for site in complex_df["site"].unique():
        site_df = complex_df[complex_df["site"] == site]
        if "azimuth_deg" in site_df.columns and "elevation_deg" in site_df.columns:
            # Polar plot: azimuth as angle, elevation as radius (90 - elev for proper display)
            fig.add_trace(go.Scatterpolar(
                r=90 - site_df["elevation_deg"],
                theta=site_df["azimuth_deg"],
                mode="lines+markers",
                name=site,
                line={"width": 2},
                marker={"size": 4}
            ))
    
    # Add 10° elevation circle
    theta = np.linspace(0, 360, 100)
    fig.add_trace(go.Scatterpolar(
        r=[80] * 100, theta=theta,
        mode="lines", name="10° Mask", line={"color": "red", "dash": "dash", "width": 2}
    ))
    
    fig.update_layout(
        polar={
            "radialaxis": {"range": [0, 90], "tickvals": [0, 30, 60, 90], "ticktext": ["90°", "60°", "30°", "0°"]},
            "angularaxis": {"direction": "clockwise", "rotation": 90}
        },
        height=400, margin={"l": 0, "r": 0, "t": 30, "b": 0}, showlegend=True
    )
    st.plotly_chart(fig, width="stretch")


# =========================================================================
# RANGE & RANGE RATE
# =========================================================================
st.markdown("---")
st.subheader("Range & Range Rate")
explain("dsn.range")

c1, c2 = st.columns(2)

with c1:
    if "range_km" in df.columns:
        fig = px.line(df, x="epoch", y="range_km", color="site", facet_col="complex", title="Range to Spacecraft (km)")
        st.plotly_chart(fig, width="stretch")

with c2:
    if "range_rate_kms" in df.columns:
        fig = px.line(df, x="epoch", y="range_rate_kms", color="site", facet_col="complex", title="Range Rate (km/s)")
        st.plotly_chart(fig, width="stretch")


# =========================================================================
# LIGHT TIME & COMMUNICATION WINDOWS
# =========================================================================
st.markdown("---")
st.subheader("Communication Windows")
explain("dsn.windows")

if "visible" in df.columns and "light_time_s" in df.columns:
    # Find continuous visibility windows per site
    windows = []
    for site in df["site"].unique():
        site_df = df[df["site"] == site].sort_values("epoch")
        site_df["vis_change"] = site_df["visible"].astype(int).diff()
        
        window_start = None
        for _, row in site_df.iterrows():
            if row["vis_change"] == 1:  # Became visible
                window_start = row["epoch"]
            elif row["vis_change"] == -1 and window_start is not None:  # Became invisible
                windows.append({
                    "site": site,
                    "complex": row.get("complex", ""),
                    "start": window_start,
                    "end": row["epoch"],
                    "duration_min": (row["epoch"] - window_start).total_seconds() / 60
                })
                window_start = None
        
        # Handle still-visible at end
        if window_start is not None:
            windows.append({
                "site": site,
                "complex": site_df.iloc[-1].get("complex", ""),
                "start": window_start,
                "end": site_df["epoch"].iloc[-1],
                "duration_min": (site_df["epoch"].iloc[-1] - window_start).total_seconds() / 60
            })
    
    if windows:
        win_df = pd.DataFrame(windows)
        win_df = win_df.sort_values("start")
        
        # Gantt chart
        fig = px.timeline(
            win_df, x_start="start", x_end="end", y="site", color="complex",
            title="DSN Visibility Windows (Continuous Passes)",
            hover_data=["duration_min"]
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=300, margin={"l": 0, "r": 0, "t": 40, "b": 0})
        st.plotly_chart(fig, width="stretch")
        
        # Summary table
        st.markdown("**Pass Summary**")
        summary = win_df.groupby(["site", "complex"]).agg(
            passes=("duration_min", "count"),
            total_min=("duration_min", "sum"),
            avg_min=("duration_min", "mean"),
            max_min=("duration_min", "max")
        ).round(1).reset_index()
        st.dataframe(summary, width="stretch", hide_index=True)


# =========================================================================
# RAW DATA
# =========================================================================
with st.expander("Raw Data Table"):
    display_cols = {
        "epoch": "Epoch (UTC)",
        "site": "Site",
        "complex": "Complex",
        "azimuth_deg": "Azimuth (°)",
        "elevation_deg": "Elevation (°)",
        "range_km": "Range (km)",
        "range_rate_kms": "Range Rate (km/s)",
        "light_time_s": "Light Time (s)",
        "visible": "Visible",
    }
    present = [c for c in display_cols if c in df.columns]
    st.dataframe(df[present].rename(columns=display_cols).tail(100), width="stretch", hide_index=True)