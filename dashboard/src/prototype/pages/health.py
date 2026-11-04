"""Spacecraft health page: is Orion warm enough, and does it have power?"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.src.prototype.data.backend_api import BackendAPIError
from dashboard.src.prototype.pages import _data
from dashboard.src.prototype.pages._controls import time_window
from dashboard.src.prototype.pages._explain import explain
from dashboard.src.prototype.pages._live import REFRESH_INTERVAL, plot
from dashboard.src.prototype.pages._status import POWER_STATUS, THERMAL_STATUS, status
from dashboard.src.prototype.pages._timeline import (
    break_at_jumps,
    jump_gap,
    true_intervals,
)

K_TO_C = 273.15
BAY_COLD_C = 249 - K_TO_C  # contract 02 electronics-bay band
BAY_HOT_C = 310 - K_TO_C
SOC_LOW = 20  # contract 03 power states
SOC_CRITICAL = 10
LAYOUT = {"height": 300, "margin": {"l": 0, "r": 0, "t": 10, "b": 0}, "hovermode": "x unified",
          "legend": {"orientation": "h", "y": 1.12, "x": 0}}

st.title("Spacecraft health")
st.caption("Is Orion warm enough, and does it have enough power? Both come from our simulation of the spacecraft.")

date_from, date_to, live = time_window()


def _shade(fig: go.Figure, spans, color: str, label: str) -> None:
    """Background bands for e.g. shadow periods; the first one carries the legend label."""
    for i, (start, end) in enumerate(spans):
        fig.add_vrect(x0=start, x1=end, fillcolor=color, opacity=0.15, line_width=0, layer="below",
                      name=label, showlegend=i == 0, legendgroup=label)


def _temperature_chart(thermal: pd.DataFrame, shadow) -> go.Figure:
    df = break_at_jumps(thermal.assign(bay_c=thermal["temp_electronics_bay_k"] - K_TO_C))
    fig = go.Figure()
    fig.add_hrect(y0=BAY_COLD_C, y1=BAY_HOT_C, fillcolor="green", opacity=0.08, line_width=0, layer="below",
                  name="Safe range", showlegend=True)
    _shade(fig, shadow, "gray", "In shadow")
    _shade(fig, true_intervals(thermal["timestamp_utc"], thermal["heater_active"], max_gap=jump_gap(thermal["timestamp_utc"])), "red", "Heater on")
    fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["bay_c"], name="Electronics temperature",
                             line={"color": "#1F77B4", "width": 2}, connectgaps=False,
                             hovertemplate="%{y:.1f} °C<extra></extra>"))
    fig.update_layout(**LAYOUT, yaxis_title="°C")
    fig.update_yaxes(range=[BAY_COLD_C - 10, BAY_HOT_C + 10])
    return fig


def _battery_chart(power: pd.DataFrame, shadow) -> go.Figure:
    df = break_at_jumps(power)
    fig = go.Figure()
    _shade(fig, shadow, "gray", "In shadow")
    fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["battery_soc_pct"], name="Battery charge",
                             line={"color": "#2CA02C", "width": 2}, connectgaps=False,
                             hovertemplate="%{y:.1f} %<extra></extra>"))
    fig.add_hline(y=SOC_LOW, line_dash="dash", line_color="orange", annotation_text="Low (20 %)")
    fig.add_hline(y=SOC_CRITICAL, line_dash="dash", line_color="red", annotation_text="Critical (10 %)")
    fig.update_layout(**LAYOUT, yaxis_title="%", yaxis_range=[0, 105])
    return fig


def _power_chart(power: pd.DataFrame, shadow) -> go.Figure:
    df = break_at_jumps(power.assign(made_kw=power["solar_array_power_w"] / 1000, used_kw=power["total_load_w"] / 1000))
    fig = go.Figure()
    _shade(fig, shadow, "gray", "In shadow")
    fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["made_kw"], name="Made by solar panels",
                             line={"color": "#FF7F0E", "width": 2}, connectgaps=False,
                             hovertemplate="%{y:.2f} kW<extra></extra>"))
    fig.add_trace(go.Scatter(x=df["timestamp_utc"], y=df["used_kw"], name="Used by the spacecraft",
                             line={"color": "#7F7F7F", "width": 2, "dash": "dash"}, connectgaps=False,
                             hovertemplate="%{y:.2f} kW<extra></extra>"))
    fig.update_layout(**LAYOUT, yaxis_title="kW", yaxis_rangemode="tozero")
    return fig


@st.fragment(run_every=REFRESH_INTERVAL if live else None)
def render(date_from, date_to):
    try:
        thermal = _data.synthetic_thermal(date_from, date_to)
        power = _data.synthetic_power(date_from, date_to)
        state = _data.synthetic_state(date_from, date_to)
    except BackendAPIError as e:
        st.error(str(e))
        return

    if thermal.empty and power.empty:
        st.info("No simulated telemetry in this time range. Start the physics model (see RUN_SERVICES.md).")
        return

    shadow = []
    if not state.empty:
        shadow = true_intervals(state["timestamp_utc"], state["eclipse_state"] != "SUNLIT", max_gap=jump_gap(state["timestamp_utc"]))

    if not thermal.empty:
        latest = thermal.iloc[-1]
        label, color = status(THERMAL_STATUS, latest["thermal_state"])
        st.subheader(f"Temperature: :{color}[{label}]")
        explain("health.temperature")
        plot(_temperature_chart(thermal, shadow))

    if not power.empty:
        latest = power.iloc[-1]
        label, color = status(POWER_STATUS, latest["power_state"])
        st.subheader(f"Battery: :{color}[{latest['battery_soc_pct']:.0f} % full]")
        explain("health.battery")
        plot(_battery_chart(power, shadow))

        st.subheader(f"Power: :{color}[{label}]")
        explain("health.power")
        plot(_power_chart(power, shadow))


render(date_from, date_to)
