"""Thermal subsystem page — 3-node lumped parameter model."""

from datetime import UTC, datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.src.prototype.data.backend_api import SyncBackendAPI, get_api
from dashboard.src.prototype.pages._explain import explain

st.title("Thermal Subsystem")
st.caption("3-node lumped parameter model: Sun Face | Shadow Face | Electronics Bay")


# Sidebar
with st.sidebar:
    st.header("Time Range")
    # Window anchored to the Artemis II mission/replay window (synthetic + real data span Apr 1-10, 2026)
    default_end = datetime(2026, 4, 10, 23, 59, tzinfo=UTC)
    default_start = datetime(2026, 4, 1, 0, 0, tzinfo=UTC)
    
    date_range = st.date_input(
        "Date Range (UTC)",
        value=(default_start.date(), default_end.date()),
        key="thermal_date_range"
    )
    
    t_start = st.time_input("Start time (UTC)", value=default_start.time(), key="thermal_time_start")
    t_end = st.time_input("End time (UTC)", value=default_end.time(), key="thermal_time_end")
    
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        date_from = datetime.combine(date_range[0], t_start, tzinfo=UTC)
        date_to = datetime.combine(date_range[1], t_end, tzinfo=UTC)
    else:
        date_from = default_start
        date_to = default_end
    
    limit = st.number_input("Max Points", 10, 5000, 500, 50, key="thermal_limit")
    state_filter = st.selectbox("Filter by State", ["All", "NOMINAL", "COLD_SURVIVAL", "HOT_LIMIT"], key="thermal_state_filter")
    
    if st.button("Refresh", key="thermal_refresh"):
        st.rerun()


api: SyncBackendAPI = get_api()


@st.cache_data(ttl=10)
def fetch_thermal(date_from, date_to, limit, state_filter):
    state = None if state_filter == "All" else state_filter
    return api.get_synthetic_thermal(date_from=date_from, date_to=date_to, thermal_state=state, limit=limit)


resp = fetch_thermal(date_from, date_to, limit, state_filter)
items = resp.items if resp else []

if not items:
    st.warning("No thermal data available for selected range.")
    st.stop()


df = pd.DataFrame([item.model_dump() for item in items])
df = df.sort_values("timestamp_utc")

# Convert to Celsius for display (contract fields are lowercase kelvin: *_k)
for col in ["temp_sun_face_k", "temp_shadow_face_k", "temp_electronics_bay_k"]:
    df[col.replace("_k", "_c")] = df[col] - 273.15


# =========================================================================
# CURRENT STATE HEADER
# =========================================================================
latest = df.iloc[-1]

c1, c2, c3, c4 = st.columns(4)
with c1:
    state = latest["thermal_state"]
    color = {"NOMINAL": "green", "COLD_SURVIVAL": "blue", "HOT_LIMIT": "red"}.get(state, "gray")
    st.metric("Thermal State", state)
    st.caption(f"Electronics Bay: {latest['temp_electronics_bay_c']:.1f} °C")
with c2:
    st.metric("Sun Face", f"{latest['temp_sun_face_c']:.1f} °C")
    st.caption(f"q_solar: {latest['q_solar_absorbed_w']:.0f} W")
with c3:
    st.metric("Shadow Face", f"{latest['temp_shadow_face_c']:.1f} °C")
    st.caption(f"q_radiated: {latest['q_radiated_w']:.0f} W")
with c4:
    st.metric("Heater", "ON" if latest["heater_active"] else "OFF")
    st.caption(f"Power: {latest['heater_power_w']:.0f} W" if latest["heater_active"] else "Power: 0 W")


# =========================================================================
# TEMPERATURE TIME SERIES
# =========================================================================
st.markdown("---")
st.subheader("Node Temperatures")
explain("thermal.temps")

fig = go.Figure()
fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["temp_electronics_bay_c"], name="Electronics Bay", line={"color": "#00D2FF", "width": 2}))
fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["temp_sun_face_c"], name="Sun Face", line={"color": "#FF6B6B", "width": 2}))
fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["temp_shadow_face_c"], name="Shadow Face", line={"color": "#4ECDC4", "width": 2}))

# Contract 02 bands: electronics bay cold survival < 249 K (−24.15 °C), hot limit > 310 K (36.85 °C)
fig.add_hline(y=-24.15, line_dash="dash", line_color="blue", annotation_text="Cold Survival (249 K / −24 °C)", annotation_position="bottom right")
fig.add_hline(y=36.85, line_dash="dash", line_color="red", annotation_text="Hot Limit (310 K / 37 °C)", annotation_position="top right")

fig.update_layout(
    title="Node Temperatures (°C)",
    yaxis_title="Temperature (°C)",
    height=400,
    margin={"l": 0, "r": 0, "t": 40, "b": 0},
    legend={"orientation": "h", "y": -0.15}
)
st.plotly_chart(fig, width="stretch")


# =========================================================================
# HEAT FLOWS
# =========================================================================
st.markdown("---")
st.subheader("Heat Flows")
explain("thermal.flows")

c1, c2 = st.columns(2)

with c1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["q_solar_absorbed_w"], name="Q Solar Absorbed", line={"color": "#FFA500", "width": 2}))
    fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["q_radiated_w"], name="Q Radiated", line={"color": "#AB63FA", "width": 2}))
    fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["q_internal_w"], name="Q Internal (from Power)", line={"color": "#00CC96", "width": 2}))
    if "heater_power_w" in df.columns:
        fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["heater_power_w"], name="Heater Power", line={"color": "#EF553B", "width": 2}))
    fig.update_layout(title="Heat Flows (W)", yaxis_title="Power (W)", height=350, margin={"l": 0, "r": 0, "t": 40, "b": 0}, legend={"orientation": "h", "y": -0.2})
    st.plotly_chart(fig, width="stretch")

with c2:
    # Energy balance check
    df["q_net"] = df["q_solar_absorbed_w"] + df["q_internal_w"] - df["q_radiated_w"]
    if "heater_power_w" in df.columns:
        df["q_net"] += df["heater_power_w"]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["q_net"], name="Net Heat Flow (In - Out)", line={"color": "#EF553B", "width": 2}))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(title="Energy Balance (Net Heat Flow)", yaxis_title="Net Power (W)", height=350, margin={"l": 0, "r": 0, "t": 40, "b": 0})
    st.plotly_chart(fig, width="stretch")


# =========================================================================
# HEATER TIMELINE
# =========================================================================
if "heater_active" in df.columns:
    st.markdown("---")
    st.subheader("Heater Activity Timeline")
    explain("thermal.heater")
    
    # Find heater on/off transitions
    df["heater_change"] = df["heater_active"].astype(int).diff()
    transitions = df[df["heater_change"] != 0]
    
    if not transitions.empty:
        fig = go.Figure()
        # Background: heater active periods
        heater_on = df[df["heater_active"]]
        if not heater_on.empty:
            for _, row in heater_on.iterrows():
                fig.add_vrect(
                    x0=row["timestamp_utc"],
                    x1=row["timestamp_utc"] + timedelta(seconds=60),  # approximate
                    fillcolor="red", opacity=0.1, line_width=0
                )
        
        fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["temp_electronics_bay_c"], name="Electronics Bay Temp", line={"color": "#00D2FF", "width": 2}))
        fig.update_layout(title="Heater Activity vs Electronics Bay Temp", yaxis_title="Temp (°C)", height=300, margin={"l": 0, "r": 0, "t": 40, "b": 0})
        st.plotly_chart(fig, width="stretch")
        
        # Transition table
        st.caption("Heater Transitions")
        trans_df = transitions[["timestamp_utc", "heater_active", "temp_electronics_bay_c"]].copy()
        trans_df["heater_active"] = trans_df["heater_active"].map({True: "ON", False: "OFF"})
        trans_df["temp_electronics_bay_c"] = trans_df["temp_electronics_bay_c"].round(1)
        st.dataframe(trans_df, width="stretch", hide_index=True)


# =========================================================================
# ECLIPSE CORRELATION
# =========================================================================
st.markdown("---")
st.subheader("Eclipse Correlation")
explain("thermal.eclipse")

c1, c2 = st.columns(2)

with c1:
    if "eclipse_state" in df.columns or "eclipse_fraction" in df.columns:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["temp_shadow_face_c"], name="Shadow Face", line={"color": "#4ECDC4", "width": 2}))
        if "eclipse_fraction" in df.columns:
            fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["eclipse_fraction"] * 100, name="Eclipse Fraction (%)", line={"color": "#FFA500", "width": 2}, yaxis="y2"))
        fig.update_layout(
            title="Shadow Face Temp vs Eclipse",
            yaxis_title="Temp (°C)",
            yaxis2={"title": "Eclipse %", "overlaying": "y", "side": "right", "range": [0, 100]},
            height=350, margin={"l": 0, "r": 0, "t": 40, "b": 0}, legend={"orientation": "h", "y": -0.2}
        )
        st.plotly_chart(fig, width="stretch")

with c2:
    if "eclipse_state" in df.columns:
        eclipse_counts = df["eclipse_state"].value_counts()
        fig = px.pie(values=eclipse_counts.values, names=eclipse_counts.index, title="Eclipse State Distribution")
        st.plotly_chart(fig, width="stretch")


# =========================================================================
# RAW DATA TABLE
# =========================================================================
with st.expander("Raw Data Table"):
    display_cols = {
        "timestamp_utc": "Timestamp",
        "temp_sun_face_c": "Sun Face (°C)",
        "temp_shadow_face_c": "Shadow Face (°C)",
        "temp_electronics_bay_c": "Electronics Bay (°C)",
        "q_solar_absorbed_w": "Q Solar (W)",
        "q_radiated_w": "Q Radiated (W)",
        "q_internal_w": "Q Internal (W)",
        "heater_active": "Heater",
        "heater_power_w": "Heater Power (W)",
        "thermal_state": "State",
    }
    present = [c for c in display_cols if c in df.columns or c.replace("_c", "_K") in df.columns]
    # Map display names
    rename_map = {k: v for k, v in display_cols.items() if k in present}
    # Handle C->K conversion
    df_display = df.copy()
    for k in present:
        if k in df_display.columns:
            continue
        if k.replace("_c", "_K") in df_display.columns:
            df_display[k] = df_display[k.replace("_c", "_K")] - 273.15
    
    st.dataframe(df_display[present].rename(columns=rename_map).tail(100), width="stretch", hide_index=True)