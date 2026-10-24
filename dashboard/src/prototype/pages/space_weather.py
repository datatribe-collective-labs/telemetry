"""Space Weather page — Real data: GOES protons, DONKI events, DSN geometry."""

from datetime import UTC, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.src.prototype.data.backend_api import SyncBackendAPI, get_api
from dashboard.src.prototype.pages._explain import explain

st.title("Space Weather")
st.caption("Real-time space environment data: GOES proton flux, DONKI events, DSN visibility")


# Sidebar
with st.sidebar:
    st.header("Time Range")
    # Window anchored to the Artemis II mission/replay window (synthetic + real data span Apr 1-10, 2026)
    default_end = datetime(2026, 4, 10, 23, 59, tzinfo=UTC)
    default_start = datetime(2026, 4, 1, 0, 0, tzinfo=UTC)
    
    date_range = st.date_input(
        "Date Range (UTC)",
        value=(default_start.date(), default_end.date()),
        key="sw_date_range"
    )
    
    t_start = st.time_input("Start time (UTC)", value=default_start.time(), key="space_weather_time_start")
    t_end = st.time_input("End time (UTC)", value=default_end.time(), key="space_weather_time_end")
    
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        date_from = datetime.combine(date_range[0], t_start, tzinfo=UTC)
        date_to = datetime.combine(date_range[1], t_end, tzinfo=UTC)
    else:
        date_from = default_start
        date_to = default_end
    
    limit = st.number_input("Max Points", 10, 5000, 1000, 50, key="sw_limit")
    
    if st.button("Refresh", key="sw_refresh"):
        st.rerun()


api: SyncBackendAPI = get_api()


@st.cache_data(ttl=60)
def fetch_goes(date_from, date_to, limit):
    return api.get_goes_protons(date_from=date_from, date_to=date_to, limit=limit)


@st.cache_data(ttl=300)
def fetch_donki(date_from, date_to, limit):
    return api.get_donki_events(date_from=date_from, date_to=date_to, limit=limit)


@st.cache_data(ttl=60)
def fetch_dsn(date_from, date_to, limit):
    return api.get_dsn_geometry(date_from=date_from, date_to=date_to, limit=limit)


# Fetch all
goes_resp = fetch_goes(date_from, date_to, limit)
donki_resp = fetch_donki(date_from, date_to, limit)
dsn_resp = fetch_dsn(date_from, date_to, limit)

goes_items = goes_resp.items if goes_resp else []
donki_items = donki_resp.items if donki_resp else []
dsn_items = dsn_resp.items if dsn_resp else []


# =========================================================================
# GOES PROTON FLUX
# =========================================================================
st.subheader("GOES Integral Proton Flux (ISWA/HAPI)")
explain("weather.goes")

if goes_items:
    goes_df = pd.DataFrame([item.model_dump() for item in goes_items])
    goes_df = goes_df.sort_values("time")
    
    # Identify flux columns
    flux_cols = [c for c in goes_df.columns if c.endswith("_pfu")]
    
    if flux_cols:
        c1, c2 = st.columns([3, 1])
        
        with c1:
            fig = go.Figure()
            for col in flux_cols:
                if goes_df[col].notna().any():
                    label = col.replace("_pfu", " MeV").replace("p", "≥").replace("500", "500")
                    fig.add_trace(go.Scatter(
                        x=goes_df["time"], y=goes_df[col],
                        name=label, mode="lines", line={"width": 1}
                    ))
            
            # Storm thresholds
            fig.add_hline(y=10, line_dash="dash", line_color="yellow", annotation_text="S1 Minor (10 pfu)")
            fig.add_hline(y=100, line_dash="dash", line_color="orange", annotation_text="S2 Moderate (100 pfu)")
            fig.add_hline(y=1000, line_dash="dash", line_color="red", annotation_text="S3 Strong (1000 pfu)")
            
            fig.update_layout(
                title="Integral Proton Flux (pfu)",
                yaxis_title="Flux (pfu)",
                yaxis_type="log",
                height=400, margin={"l": 0, "r": 0, "t": 40, "b": 0},
                legend={"orientation": "h", "y": -0.2}
            )
            st.plotly_chart(fig, width="stretch")
        
        with c2:
            latest = goes_df.iloc[-1]
            st.metric("Latest Time", latest["time"].strftime("%H:%M:%S UTC"))
            for col in flux_cols:
                val = latest[col]
                if pd.notna(val):
                    st.metric(col.replace("_pfu", " MeV"), f"{val:.1f} pfu")
else:
    st.info("No GOES proton data available.")


# =========================================================================
# DONKI SPACE WEATHER EVENTS
# =========================================================================
st.markdown("---")
st.subheader("NASA DONKI Events")
explain("weather.donki")

if donki_items:
    donki_df = pd.DataFrame([item.model_dump() for item in donki_items])
    donki_df = donki_df.sort_values("event_time", ascending=False)
    
    # Event type filter
    event_types = sorted(donki_df["event_type"].unique()) if "event_type" in donki_df.columns else []
    selected_types = st.multiselect("Filter by Event Type", event_types, default=event_types)
    
    if selected_types:
        donki_df = donki_df[donki_df["event_type"].isin(selected_types)]
    
    # Display table
    display_cols = ["event_time", "event_type", "event_id", "start_time", "end_time"]
    present = [c for c in display_cols if c in donki_df.columns]
    st.dataframe(
        donki_df[present].head(50),
        width="stretch",
        hide_index=True,
        column_config={
            "event_time": st.column_config.DatetimeColumn("Event Time (UTC)"),
            "start_time": st.column_config.DatetimeColumn("Start"),
            "end_time": st.column_config.DatetimeColumn("End"),
        }
    )
    
    # Event type counts
    if "event_type" in donki_df.columns:
        fig = px.bar(donki_df["event_type"].value_counts(), title="Events by Type")
        st.plotly_chart(fig, width="stretch")
else:
    st.info("No DONKI events in selected range.")


# =========================================================================
# DSN SITE GEOMETRY / VISIBILITY
# =========================================================================
st.markdown("---")
st.subheader("DSN Site Visibility")

if dsn_items:
    dsn_df = pd.DataFrame([item.model_dump() for item in dsn_items])
    dsn_df = dsn_df.sort_values("epoch")
    
    # Filter options
    c1, c2, c3 = st.columns(3)
    with c1:
        complexes = sorted(dsn_df["complex"].unique()) if "complex" in dsn_df.columns else []
        selected_complexes = st.multiselect("Complex", complexes, default=complexes)
    with c2:
        sites = sorted(dsn_df["site"].unique()) if "site" in dsn_df.columns else []
        selected_sites = st.multiselect("Site", sites, default=sites)
    with c3:
        visible_only = st.checkbox("Visible Only (elev ≥ 10°)", value=True)
    
    if selected_complexes:
        dsn_df = dsn_df[dsn_df["complex"].isin(selected_complexes)]
    if selected_sites:
        dsn_df = dsn_df[dsn_df["site"].isin(selected_sites)]
    if visible_only and "visible" in dsn_df.columns:
        dsn_df = dsn_df[dsn_df["visible"] == True]
    
    # Elevation timeline
    if "elevation_deg" in dsn_df.columns and "site" in dsn_df.columns:
        fig = go.Figure()
        for site in dsn_df["site"].unique():
            site_df = dsn_df[dsn_df["site"] == site].sort_values("epoch")
            fig.add_trace(go.Scatter(
                x=site_df["epoch"], y=site_df["elevation_deg"],
                name=site, mode="lines", line={"width": 1}
            ))
        
        fig.add_hline(y=10, line_dash="dash", line_color="red", annotation_text="10° Elevation Mask")
        fig.update_layout(
            title="DSN Site Elevation Angles",
            yaxis_title="Elevation (°)",
            height=400, margin={"l": 0, "r": 0, "t": 40, "b": 0},
            legend={"orientation": "h", "y": -0.2}
        )
        st.plotly_chart(fig, width="stretch")
    
    # Range & rate
    c1, c2 = st.columns(2)
    with c1:
        if "range_km" in dsn_df.columns:
            fig = px.line(dsn_df, x="epoch", y="range_km", color="site", title="Range (km)")
            st.plotly_chart(fig, width="stretch")
    with c2:
        if "range_rate_kms" in dsn_df.columns:
            fig = px.line(dsn_df, x="epoch", y="range_rate_kms", color="site", title="Range Rate (km/s)")
            st.plotly_chart(fig, width="stretch")
    
    # Current visibility summary
    if "visible" in dsn_df.columns:
        st.markdown("**Current Visibility**")
        latest_vis = dsn_df.sort_values("epoch").groupby("site").last().reset_index()
        vis_cols = st.columns(len(latest_vis))
        for i, (_, row) in enumerate(latest_vis.iterrows()):
            with vis_cols[i]:
                status = "VISIBLE" if row.get("visible") else "BELOW HORIZON"
                elev = row.get("elevation_deg", 0)
                st.metric(row.get("site", "?"), status, delta=f"{elev:.1f}°" if pd.notna(elev) else "N/A")
else:
    st.info("No DSN geometry data available.")


# =========================================================================
# COMBINED SPACE WEATHER CONTEXT
# =========================================================================
if goes_items and donki_items:
    st.markdown("---")
    st.subheader("Combined Context: Proton Flux + Events")
    explain("weather.combined")
    
    goes_df = pd.DataFrame([item.model_dump() for item in goes_items]).sort_values("time")
    donki_df = pd.DataFrame([item.model_dump() for item in donki_items]).sort_values("event_time")
    
    fig = go.Figure()
    
    # P1 flux
    if "p1_pfu" in goes_df.columns:
        fig.add_trace(go.Scatter(
            x=goes_df["time"], y=goes_df["p1_pfu"],
            name="≥1 MeV", line={"color": "#EF553B", "width": 1}, yaxis="y"
        ))
    
    # DONKI events as markers
    for _, event in donki_df.iterrows():
        if pd.notna(event.get("event_time")):
            etype = event.get("event_type", "?")
            color = {"CME": "blue", "SEP": "red", "FLR": "orange", "GST": "purple"}.get(etype, "gray")
            fig.add_vline(
                x=event["event_time"], line_dash="dash", line_color=color,
                annotation_text=f"{etype}: {event.get('event_id', '')}", annotation_position="top"
            )
    
    fig.add_hline(y=10, line_dash="dot", line_color="yellow")
    fig.add_hline(y=100, line_dash="dot", line_color="orange")
    fig.add_hline(y=1000, line_dash="dot", line_color="red")
    
    fig.update_layout(
        title="Proton Flux with DONKI Event Markers",
        yaxis_title="P1 Flux (pfu)", yaxis_type="log",
        height=400, margin={"l": 0, "r": 0, "t": 40, "b": 0}
    )
    st.plotly_chart(fig, width="stretch")