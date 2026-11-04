"""Mission page (landing): where is Orion, and is it OK?"""

from datetime import datetime

import streamlit as st

from dashboard.src.prototype.data.backend_api import BackendAPIError
from dashboard.src.prototype.pages import _data
from dashboard.src.prototype.pages._controls import time_window
from dashboard.src.prototype.pages._explain import data_badge, explain
from dashboard.src.prototype.pages._live import REFRESH_INTERVAL, plot
from dashboard.src.prototype.pages._status import (
    POWER_STATUS,
    THERMAL_STATUS,
    is_ok,
    status,
)
from dashboard.src.prototype.pages._trajectory import (
    orion_readout,
    position_frozen,
    trajectory_map,
)

STALE_AFTER_S = 15

st.title("Artemis II: where is Orion?")
st.markdown(
    f"{data_badge('real')} published by NASA/JPL · {data_badge('synthetic')} "
    f"simulated by our digital twin · {data_badge('placeholder')} not simulated yet"
)

date_from, date_to, live = time_window()
view = st.segmented_control("Map view", ["Top-down", "3D"], default="Top-down", key="mission_view")


def _health_strip(thermal, power) -> None:
    """Plain-language status tiles from the latest thermal and power rows."""
    thermal_label, thermal_color = status(THERMAL_STATUS, thermal["thermal_state"])
    power_label, power_color = status(POWER_STATUS, power["power_state"])
    attention = [label for label, state in ((thermal_label, thermal["thermal_state"]), (power_label, power["power_state"]))
                 if not is_ok(state)]
    if attention:
        st.warning(f"**Needs attention:** {', '.join(attention)}.")
    else:
        st.success("**All simulated systems are OK.**")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("**Temperature**")
        st.markdown(f"### :{thermal_color}[{thermal_label}]")
        st.caption(f"Electronics at {thermal['temp_electronics_bay_k'] - 273.15:.0f} °C (safe: −24 to 37 °C)")
    with c2:
        st.markdown("**Power**")
        st.markdown(f"### :{power_color}[{power_label}]")
        st.caption(f"Battery {power['battery_soc_pct']:.0f} % · solar panels {power['solar_array_power_w'] / 1000:.1f} kW")
    with c3:
        st.markdown("**Radio link**")
        st.markdown("### :gray[Not simulated yet]")
        st.caption("Which antennas can reach Orion: see Space environment.")
    with c4:
        st.markdown("**Radiation**")
        st.markdown("### :gray[Not simulated yet]")
        st.caption("Real solar particle levels: see Space environment.")


def _staleness(tick: datetime) -> None:
    """Warn when the replay has stopped producing ticks (live mode only)."""
    now = datetime.now().astimezone()
    last = st.session_state.get("mission_last_tick")
    if last is None or last[0] != tick:
        last = st.session_state["mission_last_tick"] = (tick, now)
    idle_s = (now - last[1]).total_seconds()
    if idle_s > STALE_AFTER_S:
        st.warning(f"The simulation hasn't moved for {idle_s:.0f} s. Is the physics model running?")


@st.fragment(run_every=REFRESH_INTERVAL if live else None)
def render(date_from, date_to, live, three_d):
    try:
        syn = _data.synthetic_state(date_from, date_to)
        real = _data.real_orion(date_from, date_to)
        thermal = _data.synthetic_thermal(date_from, date_to)
        power = _data.synthetic_power(date_from, date_to)
    except BackendAPIError as e:
        st.error(str(e))
        return

    if syn.empty and real.empty:
        st.info("No trajectory data yet. Start the physics model and run the JPL Horizons ingest (see RUN_SERVICES.md).")
        return

    if not syn.empty:
        orion_readout(syn)
        if position_frozen(syn):
            st.info("Orion's simulated position is on hold: NASA's trajectory data for the flight "
                    "starts on Apr 2 at 02:00 UTC (and ends before splashdown), so outside that span "
                    "the twin holds Orion at the nearest known point. The clock keeps running.")
        if live:
            _staleness(syn["timestamp_utc"].iloc[-1])

    explain("mission.map")
    plot(trajectory_map(real, syn, three_d=three_d))

    st.subheader("How is the spacecraft doing?")
    explain("mission.health")
    if thermal.empty or power.empty:
        st.info("No simulated telemetry in this time range. Start the physics model to see spacecraft health.")
    else:
        _health_strip(thermal.iloc[-1], power.iloc[-1])


render(date_from, date_to, live, view == "3D")
