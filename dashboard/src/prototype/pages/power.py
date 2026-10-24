"""Power subsystem page — Solar array, battery, load balance."""

from datetime import UTC, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.src.prototype.data.backend_api import SyncBackendAPI, get_api
from dashboard.src.prototype.pages._explain import explain

st.title("Power Subsystem")
st.caption("Orion ESM: 4-wing solar array (56 m²) | Li-ion battery (100 Ah, 28 V)")


# Sidebar
with st.sidebar:
    st.header("Time Range")
    # Window anchored to the Artemis II mission/replay window (synthetic + real data span Apr 1-10, 2026)
    default_end = datetime(2026, 4, 10, 23, 59, tzinfo=UTC)
    default_start = datetime(2026, 4, 1, 0, 0, tzinfo=UTC)
    
    date_range = st.date_input(
        "Date Range (UTC)",
        value=(default_start.date(), default_end.date()),
        key="power_date_range"
    )
    
    t_start = st.time_input("Start time (UTC)", value=default_start.time(), key="power_time_start")
    t_end = st.time_input("End time (UTC)", value=default_end.time(), key="power_time_end")
    
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        date_from = datetime.combine(date_range[0], t_start, tzinfo=UTC)
        date_to = datetime.combine(date_range[1], t_end, tzinfo=UTC)
    else:
        date_from = default_start
        date_to = default_end
    
    limit = st.number_input("Max Points", 10, 5000, 500, 50, key="power_limit")
    state_filter = st.selectbox("Filter by State", ["All", "NOMINAL", "BATTERY_DISCHARGE", "LOW_POWER_MODE", "CRITICAL"], key="power_state_filter")
    
    if st.button("Refresh", key="power_refresh"):
        st.rerun()


api: SyncBackendAPI = get_api()


@st.cache_data(ttl=10)
def fetch_power(date_from, date_to, limit, state_filter):
    state = None if state_filter == "All" else state_filter
    return api.get_synthetic_power(date_from=date_from, date_to=date_to, power_state=state, limit=limit)


resp = fetch_power(date_from, date_to, limit, state_filter)
items = resp.items if resp else []

if not items:
    st.warning("No power data available for selected range.")
    st.stop()


df = pd.DataFrame([item.model_dump() for item in items])
df = df.sort_values("timestamp_utc")


# =========================================================================
# CURRENT STATE HEADER
# =========================================================================
latest = df.iloc[-1]

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    state = latest["power_state"]
    color = {"NOMINAL": "green", "BATTERY_DISCHARGE": "orange", "LOW_POWER_MODE": "red", "CRITICAL": "red"}.get(state, "gray")
    st.metric("Power State", state)
with c2:
    st.metric("Battery SOC", f"{latest['battery_soc_pct']:.1f} %")
    st.caption("CRITICAL ≤ 10% | LOW_POWER ≤ 20%")
with c3:
    st.metric("Bus Voltage", f"{latest['battery_voltage_v']:.2f} V")
with c4:
    st.metric("Array Power", f"{latest['solar_array_power_w']:.0f} W")
    st.caption(f"Efficiency: {latest['array_efficiency']:.1%}")
with c5:
    st.metric("Total Load", f"{latest['total_load_w']:.0f} W")
    st.caption(f"Net: {latest['net_power_w']:.0f} W")


# =========================================================================
# POWER BALANCE WATERFALL
# =========================================================================
st.markdown("---")
st.subheader("Power Balance")
explain("power.balance")

fig = go.Figure()

# Stacked area: generation vs loads
fig.add_trace(go.Scatter(
    x=df["timestamp_utc"], y=df["solar_array_power_w"],
    name="Solar Array", fill="tozeroy", line={"color": "#FFA500", "width": 1}
))
fig.add_trace(go.Scatter(
    x=df["timestamp_utc"], y=-df["total_load_w"],
    name="Total Load", fill="tozeroy", line={"color": "#EF553B", "width": 1}
))
fig.add_trace(go.Scatter(
    x=df["timestamp_utc"], y=df["net_power_w"],
    name="Net Power", line={"color": "#00D2FF", "width": 2, "dash": "dash"}
))

fig.add_hline(y=0, line_dash="dash", line_color="gray")

fig.update_layout(
    title="Power Balance (Generation vs Loads)",
    yaxis_title="Power (W)",
    height=400,
    margin={"l": 0, "r": 0, "t": 40, "b": 0},
    legend={"orientation": "h", "y": -0.15}
)
st.plotly_chart(fig, width="stretch")


# =========================================================================
# BATTERY STATE
# =========================================================================
st.markdown("---")
st.subheader("Battery State")
explain("power.battery")

c1, c2 = st.columns(2)

with c1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["battery_soc_pct"], name="SOC", line={"color": "#00CC96", "width": 2}))
    fig.add_hline(y=100, line_dash="dash", line_color="green", annotation_text="Full")
    fig.add_hline(y=20, line_dash="dash", line_color="orange", annotation_text="LOW_POWER_MODE threshold")
    fig.add_hline(y=10, line_dash="dash", line_color="red", annotation_text="CRITICAL threshold")
    fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Depleted")
    fig.update_layout(title="Battery State of Charge (%)", yaxis_title="SOC (%)", yaxis_range=[-5, 105], height=350, margin={"l": 0, "r": 0, "t": 40, "b": 0})
    st.plotly_chart(fig, width="stretch")

with c2:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["battery_voltage_v"], name="Voltage", line={"color": "#AB63FA", "width": 2}))
    fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["battery_current_a"], name="Current (A)", line={"color": "#EF553B", "width": 2}, yaxis="y2"))
    fig.update_layout(
        title="Battery Voltage & Current",
        yaxis_title="Voltage (V)",
        yaxis2={"title": "Current (A)", "overlaying": "y", "side": "right"},
        height=350, margin={"l": 0, "r": 0, "t": 40, "b": 0}, legend={"orientation": "h", "y": -0.2}
    )
    st.plotly_chart(fig, width="stretch")


# =========================================================================
# BATTERY CURRENT TIMELINE
# =========================================================================
st.markdown("---")
st.subheader("Battery Current (Charge/Discharge)")

fig = go.Figure()

# Color by charge/discharge
colors = ["green" if c > 0 else "red" for c in df["battery_current_a"]]
fig.add_trace(go.Bar(
    x=df["timestamp_utc"], y=df["battery_current_a"],
    name="Battery Current", marker_color=colors, width=60000  # 1 min bars
))

fig.add_hline(y=0, line_color="gray")
fig.update_layout(
    title="Battery Current (A) — Green=Charge, Red=Discharge",
    yaxis_title="Current (A)",
    height=300, margin={"l": 0, "r": 0, "t": 40, "b": 0}
)
st.plotly_chart(fig, width="stretch")


# =========================================================================
# AVAILABLE POWER & MARGIN
# =========================================================================
st.markdown("---")
st.subheader("Available Power & Margin")
explain("power.available")

c1, c2 = st.columns(2)

with c1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["available_power_w"], name="Available Power", line={"color": "#00D2FF", "width": 2}))
    fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["solar_array_power_w"], name="Array Power", line={"color": "#FFA500", "width": 1, "dash": "dot"}))
    fig.add_hline(y=800, line_dash="dash", line_color="orange", annotation_text="Essential Load Floor")
    fig.update_layout(title="Available Power (W)", yaxis_title="Power (W)", height=350, margin={"l": 0, "r": 0, "t": 40, "b": 0})
    st.plotly_chart(fig, width="stretch")

with c2:
    # Power state distribution
    state_counts = df["power_state"].value_counts()
    colors_map = {"NOMINAL": "#00CC96", "BATTERY_DISCHARGE": "#FFA500", "LOW_POWER_MODE": "#EF553B", "CRITICAL": "#EF553B"}
    fig = px.pie(
        values=state_counts.values, names=state_counts.index,
        title="Power State Distribution",
        color=state_counts.index,
        color_discrete_map=colors_map
    )
    st.plotly_chart(fig, width="stretch")


# =========================================================================
# ARRAY EFFICIENCY & DEGRADATION
# =========================================================================
st.markdown("---")
st.subheader("Array Efficiency & Degradation")
explain("power.efficiency")

c1, c2 = st.columns(2)

with c1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["array_efficiency"], name="Effective Efficiency", line={"color": "#00CC96", "width": 2}))
    fig.add_hline(y=0.30, line_dash="dash", line_color="gray", annotation_text="BOL (30%)")
    fig.update_layout(title="Effective Array Efficiency", yaxis_title="Efficiency", yaxis_tickformat=".1%", height=350, margin={"l": 0, "r": 0, "t": 40, "b": 0})
    st.plotly_chart(fig, width="stretch")

with c2:
    if "array_efficiency" in df.columns:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["battery_soc_pct"], y=df["array_efficiency"],
            mode="markers", name="Efficiency vs SOC",
            marker={"color": df["timestamp_utc"].astype(int) // 10**9, "colorscale": "Viridis", "showscale": True, "colorbar": {"title": "Time"}}
        ))
        fig.update_layout(title="Efficiency vs SOC (colored by time)", xaxis_title="SOC (%)", yaxis_title="Efficiency", height=350, margin={"l": 0, "r": 0, "t": 40, "b": 0})
        st.plotly_chart(fig, width="stretch")


# =========================================================================
# RAW DATA TABLE
# =========================================================================
with st.expander("Raw Data Table"):
    display_cols = {
        "timestamp_utc": "Timestamp",
        "solar_array_power_w": "Array (W)",
        "array_efficiency": "Efficiency",
        "total_load_w": "Load (W)",
        "battery_soc_pct": "SOC (%)",
        "battery_voltage_v": "Voltage (V)",
        "battery_current_a": "Current (A)",
        "net_power_w": "Net (W)",
        "available_power_w": "Available (W)",
        "power_state": "State",
    }
    present = [c for c in display_cols if c in df.columns]
    st.dataframe(df[present].rename(columns=display_cols).tail(100), width="stretch", hide_index=True)