"""Mission page (landing): where is Orion, and is it OK?

Live: follows the simulation's newest tick. With Live off, a replay slider (and a
Play toggle) moves Orion and the Moon along the real NASA/JPL path inside the
sidebar's time range, so the page works without the physics model running.
"""

from datetime import UTC, datetime, timedelta

import streamlit as st

from dashboard.src.prototype.data.backend_api import BackendAPIError
from dashboard.src.prototype.views import _data
from dashboard.src.prototype.views._controls import time_window
from dashboard.src.prototype.views._explain import data_badge, explain
from dashboard.src.prototype.views._link import (
    LinkGap,
    duration_text,
    gap_at,
    link_gaps,
    link_timeline,
)
from dashboard.src.prototype.views._live import REFRESH_INTERVAL, plot
from dashboard.src.prototype.views._phases import (
    milestones,
    mission_phases,
    phase_at,
    timeline_strip,
)
from dashboard.src.prototype.views._status import (
    EXPECTED_GAPS,
    POWER_STATUS,
    THERMAL_STATUS,
    format_dose,
    is_ok,
    link_is_expected,
    link_needs_attention,
    link_status,
    radiation_zone,
    status,
)
from dashboard.src.prototype.views._trajectory import (
    at_time,
    orion_readout,
    position_frozen,
    trajectory_map,
    up_to,
)

STALE_AFTER_S = 15
REPLAY_KEY = "mission_replay_at"
PLAY_KEY = "mission_replay_playing"
PLAY_INTERVAL = "1s"
PLAY_STEP = timedelta(hours=2)  # mission time per Play tick: the whole flight in ~2 min
REAL_DATA_SPAN = "Apr 2, 02:00 – Apr 10, 23:00 UTC"

st.title("Artemis II: where is Orion?")
st.markdown(
    f"{data_badge('real')} published by NASA/JPL · {data_badge('synthetic')} simulated by our digital twin"
)

date_from, date_to, live = time_window()
left, right = st.columns([3, 1], vertical_alignment="bottom")
with left:
    view = st.segmented_control("Map view", ["Top-down", "3D"], default="Top-down", key="mission_view")
playing = False
if not live:
    with right:
        playing = st.toggle("▶ Play replay", key=PLAY_KEY,
                            help=f"Move the replay forward by {PLAY_STEP.seconds // 3600} h of mission time "
                                 "every second, up to the end of the sidebar's time range.")


def _replay_slider(date_from: datetime, date_to: datetime, playing: bool) -> datetime:
    """The replay moment, advanced by PLAY_STEP on each run while playing.

    Play stops at the end of the range; pressing Play there starts over. The value
    lives in session state (set before the slider is drawn, so no conflicting default).
    """
    lo, hi = date_from.replace(tzinfo=None), date_to.replace(tzinfo=None)
    t = st.session_state.get(REPLAY_KEY)
    started = playing and not st.session_state.get("mission_replay_was_playing", False)
    if t is None or not lo <= t <= hi:
        t = lo if playing else hi
    elif playing:
        t = lo if started and t >= hi else min(t + PLAY_STEP, hi)
    st.session_state["mission_replay_was_playing"] = playing
    st.session_state[REPLAY_KEY] = t
    st.slider("Replay: show the spacecraft at (UTC)", min_value=lo, max_value=hi, step=timedelta(hours=1),
              format="MMM D, HH:mm", key=REPLAY_KEY)
    return st.session_state[REPLAY_KEY].replace(tzinfo=UTC)


def _radio_tile(link, gap: LinkGap | None) -> None:
    st.markdown("**Radio link**")
    if link is None:
        st.markdown("### :gray[No data]")
        st.caption("No simulated radio link for this moment.")
        return
    label, color = link_status(link["comm_state"], link["link_loss_reason"])
    st.markdown(f"### :{color}[{label}]")
    if link["comm_state"] != "NO_LINK":
        st.caption(f"{link['data_rate_kbps'] / 1000:.2f} Mbps · link margin {link['link_margin_db']:.0f} dB")
    elif gap is not None:
        st.caption(f"No link for {duration_text(link['timestamp_utc'] - gap.start)}")
    else:
        st.caption("No link")


def _radiation_tile(radiation) -> None:
    st.markdown("**Radiation**")
    if radiation is None:
        st.markdown("### :gray[No data]")
        st.caption("No simulated radiation for this moment.")
        return
    label, color, sentence = radiation_zone(radiation["radiation_zone"])
    st.markdown(f"### :{color}[{label}]")
    st.caption(f"{format_dose(radiation['cumulative_dose_krad'])} so far. {sentence} "
               "Simulated at one cabin sensor, not the crew's actual dose.")


def _health_strip(thermal, power, link, radiation, gap: LinkGap | None) -> None:
    """Plain-language status tiles from the latest row of each model."""
    thermal_label, thermal_color = status(THERMAL_STATUS, thermal["thermal_state"])
    power_label, power_color = status(POWER_STATUS, power["power_state"])
    attention = [label for label, state in ((thermal_label, thermal["thermal_state"]), (power_label, power["power_state"]))
                 if not is_ok(state)]
    expected_gap = None
    if link is not None:
        if link_needs_attention(link["comm_state"], link["link_loss_reason"]):
            attention.append(link_status(link["comm_state"], link["link_loss_reason"])[0])
        elif link_is_expected(link["comm_state"], link["link_loss_reason"]):
            expected_gap = f"Earth can't reach Orion right now: {EXPECTED_GAPS[link['link_loss_reason']]}. This gap is expected."
    if attention:
        st.warning(f"**Needs attention:** {', '.join(attention)}." + (f" {expected_gap}" if expected_gap else ""))
    elif expected_gap:
        st.info(f"**All simulated systems are OK.** {expected_gap}")
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
        _radio_tile(link, gap)
    with c4:
        _radiation_tile(radiation)


def _staleness(tick: datetime) -> None:
    """Warn when the replay has stopped producing ticks (live mode only)."""
    now = datetime.now().astimezone()
    last = st.session_state.get("mission_last_tick")
    if last is None or last[0] != tick:
        last = st.session_state["mission_last_tick"] = (tick, now)
    idle_s = (now - last[1]).total_seconds()
    if idle_s > STALE_AFTER_S:
        st.warning(f"The simulation hasn't moved for {idle_s:.0f} s. Is the physics model running?")


def _optional(load, what: str):
    """Moon and timeline data only add context: if missing, say so and carry on."""
    try:
        return load()
    except BackendAPIError:
        st.caption(f"{what} unavailable (see RUN_SERVICES.md for the ingest jobs).")
        return None


def _synthetic(table: str, date_from, date_to, live: bool):
    """Live: up to the simulator's position. Replay: the stored mission, so any moment works."""
    if live:
        return getattr(_data, f"synthetic_{table}")(date_from, date_to)
    return _data.stored_mission(table, date_from, date_to)


def _latest(df, replay_at):
    """The newest row at or before the moment shown, or None."""
    rows = up_to(df, replay_at)
    return None if rows.empty else rows.iloc[-1]


@st.fragment(run_every=REFRESH_INTERVAL if live else (PLAY_INTERVAL if playing else None))
def render(date_from, date_to, live, three_d, playing):
    replay_at = None if live else _replay_slider(date_from, date_to, playing)
    try:
        syn = _synthetic("state", date_from, date_to, live)
        real = _data.real_orion(date_from, date_to)
        thermal = _synthetic("thermal", date_from, date_to, live)
        power = _synthetic("power", date_from, date_to, live)
        comms = _synthetic("comms", date_from, date_to, live)
        radiation = _synthetic("radiation", date_from, date_to, live)
        stored_comms = _data.stored_mission("comms", date_from, date_to)
    except BackendAPIError as e:
        st.error(str(e))
        return
    moon = _optional(lambda: _data.moon(date_from, date_to), "The Moon's position is")
    events = _optional(_data.mission_events, "The mission timeline is")

    if syn.empty and real.empty:
        st.info("No trajectory data yet. Start the physics model and run the JPL Horizons ingest (see RUN_SERVICES.md).")
        return

    # The moment this page shows: newest simulated tick (live), or the replay time,
    # placed on the real path (falling back to the simulation before/after it).
    if live:
        now = syn.iloc[-1] if not syn.empty else None
        now_t = now["timestamp_utc"] if now is not None else None
    else:
        now = at_time(real, replay_at)
        if now is None:
            now = at_time(up_to(syn, replay_at), replay_at)
        now_t = replay_at
    moon_now = at_time(moon, now_t) if moon is not None and now_t is not None else None

    if not live:
        st.markdown(f"{data_badge('real')} Replaying the path Orion really flew. Move the slider, or press "
                    "**Play**; turn **Live** on in the sidebar to follow the simulation.")
    if now is not None:
        if not live and at_time(real, replay_at) is None:
            st.caption(f"{data_badge('synthetic')} NASA/JPL's trajectory data covers {REAL_DATA_SPAN}; "
                       "for this moment the numbers come from our simulation.")
        orion_readout(now, moon_now)
    elif not live:
        st.info(f"No position for this moment: NASA/JPL's trajectory data covers {REAL_DATA_SPAN}.")
    if live and not syn.empty:
        if position_frozen(syn):
            st.info("Orion's simulated position is on hold: NASA's trajectory data for the flight "
                    "starts on Apr 2 at 02:00 UTC (and ends before splashdown), so outside that span "
                    "the twin holds Orion at the nearest known point. The clock keeps running.")
        _staleness(syn["timestamp_utc"].iloc[-1])

    phases = mission_phases(events) if events is not None else []
    if phases:
        stage = phase_at(phases, now_t) if now_t is not None else None
        st.markdown(f"**Mission stage:** {stage.name if stage else 'outside the planned timeline'}")
        explain("mission.timeline")
        plot(timeline_strip(phases, milestones(events), now_t))

    explain("mission.map")
    plot(trajectory_map(real, syn, three_d=three_d, moon_df=moon, replay_at=replay_at))

    st.subheader("How is the spacecraft doing?")
    explain("mission.health")
    thermal, power = up_to(thermal, replay_at), up_to(power, replay_at)
    # The stored mission, unless the first run hasn't been stored yet (it is cached for a minute).
    whole_mission = stored_comms if len(stored_comms) >= len(comms) else comms
    gaps = link_gaps(whole_mission)
    if thermal.empty or power.empty:
        st.info("No simulated telemetry in this time range. Start the physics model to see spacecraft health.")
    else:
        if not live:
            st.caption(f"Simulated state at {thermal['timestamp_utc'].iloc[-1]:%b %d, %H:%M} UTC, "
                       "the last simulated moment up to the replay time.")
        link = _latest(comms, replay_at)
        gap = gap_at(gaps, link["timestamp_utc"]) if link is not None else None
        _health_strip(thermal.iloc[-1], power.iloc[-1], link, _latest(radiation, replay_at), gap)

    if not whole_mission.empty:
        st.subheader("When could Earth hear Orion?")
        explain("mission.link")
        plot(link_timeline(gaps, whole_mission["timestamp_utc"].iloc[0], whole_mission["timestamp_utc"].iloc[-1], now_t))


render(date_from, date_to, live, view == "3D", playing)
