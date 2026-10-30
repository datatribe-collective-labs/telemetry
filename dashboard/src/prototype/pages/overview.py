"""Overview / Health page — Mission Control at a glance."""

from datetime import UTC, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.src.prototype.data.backend_api import SyncBackendAPI, get_api
from dashboard.src.prototype.pages._explain import explain

st.title("Artemis II Digital Twin — Overview")
st.caption("Synthetic telemetry from physics models | Real data from JPL/NASA APIs")


# Sidebar controls
with st.sidebar:
    st.header("Time Range")
    # Window anchored to the Artemis II mission/replay window (synthetic + real data span Apr 1-10, 2026)
    default_end = datetime(2026, 4, 10, 23, 59, tzinfo=UTC)
    default_start = datetime(2026, 4, 1, 0, 0, tzinfo=UTC)
    
    date_range = st.date_input(
        "Date Range (UTC)",
        value=(default_start.date(), default_end.date()),
    )
    
    t_start = st.time_input("Start time (UTC)", value=default_start.time(), key="overview_time_start")
    t_end = st.time_input("End time (UTC)", value=default_end.time(), key="overview_time_end")
    
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        date_from = datetime.combine(date_range[0], t_start, tzinfo=UTC)
        date_to = datetime.combine(date_range[1], t_end, tzinfo=UTC)
    else:
        date_from = default_start
        date_to = default_end
    
    limit = st.number_input("Max Points", min_value=10, max_value=5000, value=500, step=50)
    auto_refresh = st.checkbox("Auto-refresh (10s)", value=False)
    
    if st.button("Refresh Now"):
        st.rerun()


# API client
@st.cache_resource
def get_api_client():
    return get_api()


api: SyncBackendAPI = get_api_client()


# Fetch latest packet for health status
@st.cache_data(ttl=5)
def fetch_latest_packet():
    return api.get_latest_packet()


@st.cache_data(ttl=10)
def fetch_packet_history(date_from, date_to, limit):
    return api.get_synthetic_packet(date_from=date_from, date_to=date_to, limit=limit)


# Main layout
latest = fetch_latest_packet()

if latest is None:
    st.warning("No synthetic telemetry data available. Ensure physics models are running and publishing to Kafka.")
    st.info("Backend: http://localhost:8000 | Check `/telemetry/synthetic/latest` endpoint")
else:
    # =========================================================================
    # HEADER: Mission Phase + All Nominal
    # =========================================================================
    col_mission, col_nominal, col_met = st.columns([2, 1, 1])
    
    with col_mission:
        st.subheader("Mission Status")
        explain("overview.status")
        # Calculate MET from liftoff (Artemis II: April 2026)
        liftoff = datetime(2026, 4, 1, 22, 35, 0, tzinfo=UTC)
        met = latest.timestamp_utc - liftoff
        met_str = f"{met.days}d {met.seconds//3600:02d}:{(met.seconds%3600)//60:02d}:{met.seconds%60:02d}"
        st.metric("Mission Elapsed Time (MET)", met_str)
        
        # Mission phase from planned attitude
        from contracts.planned_attitude import resolve_attitude
        attitude_mode, mode_def = resolve_attitude(met)
        st.caption(f"Attitude: **{attitude_mode.value}** — {mode_def.get('description', 'N/A')}")
    
    with col_nominal:
        st.subheader("All Nominal")
        if latest.all_nominal:
            st.success("**ALL NOMINAL**")
        else:
            st.error("**ANOMALY DETECTED**")
        st.caption("Thermal ∧ Power ∧ Comms = NOMINAL")
    
    with col_met:
        st.subheader("Timestamp")
        st.metric("Latest Tick", latest.timestamp_utc.strftime("%H:%M:%S UTC"))
        st.caption(f"Date: {latest.timestamp_utc.strftime('%Y-%m-%d')}")


    # =========================================================================
    # SUBSYSTEM HEALTH GRID (4 quadrants)
    # =========================================================================
    st.markdown("---")
    st.subheader("Subsystem Health")
    explain("overview.subsystems")
    
    col_thermal, col_power, col_comms, col_rad = st.columns(4)
    
    # Thermal card
    with col_thermal:
        thermal_state = latest.thermal_state
        color = {"NOMINAL": "green", "COLD_SURVIVAL": "blue", "HOT_LIMIT": "red"}.get(thermal_state, "gray")
        st.markdown(f"### :{color}[Thermal: {thermal_state}]")
        st.metric("Electronics Bay", f"{latest.temp_electronics_bay_k - 273.15:.1f} °C")
        st.metric("Sun Face", f"{latest.temp_sun_face_k - 273.15:.1f} °C")
        st.metric("Shadow Face", f"{latest.temp_shadow_face_k - 273.15:.1f} °C")
        st.caption(f"Heater: {'ON' if latest.heater_active else 'OFF'}")
    
    # Power card
    with col_power:
        power_state = latest.power_state
        color = {"NOMINAL": "green", "BATTERY_DISCHARGE": "orange", "LOW_POWER_MODE": "red", "CRITICAL": "red"}.get(power_state, "gray")
        st.markdown(f"### :{color}[Power: {power_state}]")
        st.metric("Battery SOC", f"{latest.battery_soc_pct:.1f} %")
        st.metric("Bus Voltage", f"{latest.battery_voltage_v:.1f} V")
        st.metric("Array Power", f"{latest.solar_array_power_w:.0f} W")
        st.caption(f"Available: {latest.solar_array_power_w:.0f} W")
    
    # Comms card
    with col_comms:
        comm_state = latest.comm_state
        color = {"NOMINAL": "green", "DEGRADED": "orange", "NO_LINK": "red"}.get(comm_state, "gray")
        st.markdown(f"### :{color}[Comms: {comm_state}]")
        st.metric("Link Margin", f"{latest.link_margin_db:.1f} dB")
        st.metric("Data Rate", f"{latest.data_rate_kbps:.0f} kbps")
        st.metric("Signal Quality", f"{latest.signal_quality:.2f}")
    
    # Radiation card
    with col_rad:
        sep_active = latest.sep_event_active
        color = "red" if sep_active else "green"
        st.markdown(f"### :{color}[Radiation: {'SEP ACTIVE' if sep_active else 'QUIET'}]")
        st.metric("Dose Rate", f"{latest.radiation_dose_rate_mrad_hr:.3f} mrad/hr")
        st.metric("Cumulative", f"{latest.cumulative_dose_krad:.3f} krad")
        st.caption(f"SEP Event: {'YES' if sep_active else 'NO'}")


    # =========================================================================
    # KEY VITALS TIME SERIES (last 50 points)
    # =========================================================================
    st.markdown("---")
    st.subheader("Key Vitals — Recent History")
    explain("overview.vitals")
    
    history = fetch_packet_history(date_from, date_to, min(limit, 200))
    
    if history.items:
        df = pd.DataFrame([p.model_dump() for p in history.items])
        df = df.sort_values("timestamp_utc")
        
        # Convert to Celsius for display
        df["temp_electronics_bay_C"] = df["temp_electronics_bay_k"] - 273.15
        df["temp_sun_face_C"] = df["temp_sun_face_k"] - 273.15
        df["temp_shadow_face_C"] = df["temp_shadow_face_k"] - 273.15
        
        # 2x2 grid of sparklines
        c1, c2 = st.columns(2)
        
        with c1:
            # Thermal temps
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["temp_electronics_bay_C"], name="Electronics Bay", line={"color": "#00D2FF"}))
            fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["temp_sun_face_C"], name="Sun Face", line={"color": "#FF6B6B"}))
            fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["temp_shadow_face_C"], name="Shadow Face", line={"color": "#4ECDC4"}))
            fig.update_layout(title="Temperatures (°C)", height=250, margin={"l": 0, "r": 0, "t": 30, "b": 0}, legend={"orientation": "h", "y": -0.2})
            fig.add_hline(y=10, line_dash="dash", line_color="blue", annotation_text="Cold Limit")
            fig.add_hline(y=37, line_dash="dash", line_color="red", annotation_text="Hot Limit")
            st.plotly_chart(fig, width="stretch")
        
        with c2:
            # Power SOC + Array
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["battery_soc_pct"], name="SOC %", line={"color": "#00CC96"}, yaxis="y"))
            fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["solar_array_power_w"], name="Array (W)", line={"color": "#FFA500"}, yaxis="y2"))
            fig.update_layout(
                title="Battery SOC & Array Power", height=250, margin={"l": 0, "r": 0, "t": 30, "b": 0},
                yaxis={"title": "SOC %", "side": "left", "range": [0, 105]},
                yaxis2={"title": "Array Power (W)", "side": "right", "overlaying": "y"},
                legend={"orientation": "h", "y": -0.2}
            )
            fig.add_hline(y=20, line_dash="dash", line_color="orange", annotation_text="LOW_POWER_MODE")
            fig.add_hline(y=10, line_dash="dash", line_color="red", annotation_text="CRITICAL")
            st.plotly_chart(fig, width="stretch")
        
        c3, c4 = st.columns(2)
        
        with c3:
            # Comms link margin
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["link_margin_db"], name="Link Margin", line={"color": "#AB63FA"}))
            fig.update_layout(title="Comms Link Margin (dB)", height=250, margin={"l": 0, "r": 0, "t": 30, "b": 0})
            fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="NO_LINK threshold")
            fig.add_hline(y=3, line_dash="dash", line_color="orange", annotation_text="DEGRADED threshold")
            st.plotly_chart(fig, width="stretch")
        
        with c4:
            # Radiation dose rate
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["radiation_dose_rate_mrad_hr"], name="Dose Rate", line={"color": "#EF553B"}))
            fig.update_layout(title="Radiation Dose Rate (mrad/hr)", height=250, margin={"l": 0, "r": 0, "t": 30, "b": 0}, yaxis_type="log")
            st.plotly_chart(fig, width="stretch")
    
    else:
        st.info("No historical data in selected range.")


# Auto-refresh logic
if auto_refresh:
    import time
    time.sleep(10)
    st.rerun()