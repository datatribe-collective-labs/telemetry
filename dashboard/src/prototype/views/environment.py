"""Space environment page: was there a solar storm, and could Earth reach Orion?

Two answers about the whole flight, then the Sun, the three antennas and the Moon
blackout. All real data (NASA/JPL, NOAA GOES). Replaces the old Space Weather and DSN
Coverage pages.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboard.src.prototype.data.backend_api import BackendAPIError
from dashboard.src.prototype.views import _data
from dashboard.src.prototype.views._blackout import (
    BLACKOUT_END,
    BLACKOUT_START,
    DSN_STEP,
    contact_summary,
    cut_blackout,
    in_blackout,
    sites_in_view,
)
from dashboard.src.prototype.views._controls import (
    LIFTOFF,
    MISSION_END,
    MISSION_START,
    time_window,
)
from dashboard.src.prototype.views._explain import explain
from dashboard.src.prototype.views._link import REASON_COLORS, duration_text
from dashboard.src.prototype.views._live import REFRESH_INTERVAL, plot
from dashboard.src.prototype.views._status import STORM_PFU, storm_summary
from dashboard.src.prototype.views._timeline import true_intervals

# NOAA solar radiation storm scale, defined on the >=10 MeV integral proton flux.
STORM_LEVELS = [(STORM_PFU, 100, "#F2C94C", "Minor storm (S1)"), (100, 1000, "#F2994A", "Moderate storm (S2)"),
                (1000, 1e6, "#EB5757", "Strong storm (S3+)")]
EVENT_NAMES = {
    "CME": "Solar eruption (CME)", "FLR": "Solar flare", "SEP": "Solar particle event",
    "GST": "Geomagnetic storm", "HSS": "Fast solar wind", "IPS": "Shock in the solar wind",
    "RBE": "Radiation belt boost", "MPC": "Magnetopause crossing",
}
# Where each complex is, for readers who don't know the DSN.
COMPLEXES = {"Goldstone": "California, USA", "Madrid": "Spain", "Canberra": "Australia"}
COMPLEX_COLORS = {"Goldstone": "#1F77B4", "Madrid": "#9467BD", "Canberra": "#17BECF"}
MOON_COLOR = REASON_COLORS["MOON_BLOCKED"]

st.title("Was there a solar storm, and could Earth reach Orion?")
st.caption("The space weather Orion flew through, and which of NASA's big antennas could reach it. "
           "All data on this page is real, published by NASA/JPL and NOAA.")

date_from, date_to, live = time_window()


def _answers(goes: pd.DataFrame, dsn: pd.DataFrame) -> None:
    """The page's two short answers, always about the whole flight."""
    explain("environment.answers")
    left, right = st.columns(2)
    with left:
        st.markdown("**Was there a solar radiation storm?**")
        storm = storm_summary(goes, LIFTOFF)
        if storm is None:
            st.markdown("### :gray[No data]")
        else:
            st.markdown("### :orange[Yes]" if storm.storm else "### :green[No solar radiation storm]")
            st.caption(f"Solar particles peaked at **{storm.peak_pfu:.2f} pfu** on {storm.peak_time:%b %d}. "
                       f"The storm level is **{STORM_PFU} pfu**.")
    with right:
        st.markdown("**Could Earth reach Orion?**")
        if dsn.empty:
            st.markdown("### :gray[No data]")
        else:
            contact = contact_summary(dsn)
            st.markdown(f"### :blue[{contact.coverage:.0%} of the time]")
            st.caption(f"Gaps lasted up to about **{contact.longest_gap / pd.Timedelta('1h'):.0f} h**, including "
                       f"**{duration_text(BLACKOUT_END - BLACKOUT_START)}** behind the Moon (NASA's planned window).")


def _particles_chart(goes: pd.DataFrame, events: pd.DataFrame, flight_end) -> go.Figure:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.78, 0.22], vertical_spacing=0.04)
    flux = goes.dropna(subset=["p10_pfu"])
    flux = flux[flux["p10_pfu"] > 0]
    for low, high, color, label in STORM_LEVELS:
        fig.add_hrect(y0=low, y1=high, fillcolor=color, opacity=0.18, line_width=0, layer="below",
                      row=1, col=1, annotation_text=label, annotation_position="top left",
                      annotation_font_size=11)
    fig.add_vrect(x0=LIFTOFF, x1=flight_end, fillcolor="#1F77B4", opacity=0.05, line_width=0, layer="below",
                  annotation_text="Orion in flight", annotation_position="top left", annotation_font_size=11)
    fig.add_trace(go.Scatter(x=flux["time"], y=flux["p10_pfu"], name="Solar particles (≥10 MeV)",
                             line={"color": "#D62728", "width": 1.5},
                             hovertemplate="%{x|%b %d %H:%M} UTC<br>%{y:.2f} pfu<extra></extra>"), row=1, col=1)
    if not events.empty:
        names = events["event_type"].map(EVENT_NAMES).fillna(events["event_type"])
        fig.add_trace(go.Scatter(x=events["when"], y=names, mode="markers", name="Solar events (NASA DONKI)",
                                 marker={"size": 9, "symbol": "diamond", "color": "#555"},
                                 customdata=events["event_id"],
                                 hovertemplate="%{y}<br>%{x|%b %d %H:%M} UTC<br>%{customdata}<extra></extra>"),
                      row=2, col=1)
    # Log axis from just below the quietest level to just above the storm threshold (or
    # the peak), so the storm bands are always visible for comparison.
    top = max(1000.0, float(flux["p10_pfu"].max()) if not flux.empty else 0) * 3
    bottom = float(flux["p10_pfu"].min()) / 2 if not flux.empty else 0.05
    fig.update_yaxes(type="log", range=[np.log10(bottom), np.log10(top)], title_text="pfu", row=1, col=1)
    fig.update_yaxes(title_text=None, row=2, col=1)
    fig.update_layout(height=520, margin={"l": 0, "r": 0, "t": 10, "b": 0}, showlegend=False)
    return fig


def _contact_now(dsn: pd.DataFrame, now: datetime) -> None:
    """One tile per DSN complex: can it see Orion at `now`?"""
    at = dsn[dsn["epoch"] <= now]
    if at.empty:
        st.caption("Contact information starts on Apr 2, after Orion leaves Earth orbit.")
        return
    at = at[at["epoch"] == at["epoch"].max()]
    data_hour = at["epoch"].iloc[0]
    st.caption(f"At {now:%b %d, %H:%M} UTC, using the hourly NASA/JPL positions from {data_hour:%H:%M} UTC.")
    # One-way light time from Horizons; the three sites differ by milliseconds.
    delay_s = at["light_time_s"].dropna()
    if not delay_s.empty:
        one_way = float(delay_s.mean())
        st.markdown(f"A radio signal takes **{one_way:.1f} s** to reach Orion, "
                    f"so a question and its answer take **{2 * one_way:.1f} s**.")
    cols = st.columns(len(COMPLEXES))
    for col, (name, where) in zip(cols, COMPLEXES.items(), strict=True):
        row = at[at["complex"] == name]
        with col:
            st.markdown(f"**{name}** · {where}")
            if row.empty:
                st.markdown("### :gray[No data]")
                continue
            r = row.iloc[0]
            if r["visible"] and in_blackout(now):
                st.markdown("### :blue[Blocked by the Moon]")
                st.caption(f"Orion is {r['elevation_deg']:.0f}° above the horizon, but the Moon is in the way "
                           "(NASA's planned window)")
            elif r["visible"]:
                st.markdown("### :green[Can reach Orion]")
                st.caption(f"Orion is {r['elevation_deg']:.0f}° above the horizon")
            else:
                st.markdown("### :gray[Out of view]")
                st.caption("Orion is below this site's horizon")


def _windows_chart(dsn: pd.DataFrame, now: datetime | None, now_label: str) -> tuple[go.Figure, float, pd.Timedelta]:
    """Contact windows per complex with the blackout cut out, plus coverage and the longest gap."""
    fig = go.Figure()
    for name in COMPLEXES:
        site = dsn[dsn["complex"] == name]
        spans = true_intervals(site["epoch"], site["visible"].fillna(False).astype(bool), max_gap=DSN_STEP)
        for start, end in cut_blackout(spans):
            fig.add_trace(go.Bar(base=[start], x=[(end - start) / pd.Timedelta("1ms")], y=[name], orientation="h",
                                 marker_color=COMPLEX_COLORS[name], showlegend=False,
                                 hovertemplate=f"{name}<br>{start:%b %d %H:%M} → {end:%b %d %H:%M} UTC<extra></extra>"))
    contact = contact_summary(dsn)
    for start, end in contact.gaps:
        fig.add_vrect(x0=start, x1=end, fillcolor="#EB5757", opacity=0.12, line_width=0, layer="below")
    if dsn["epoch"].min() < BLACKOUT_END and dsn["epoch"].max() > BLACKOUT_START:
        fig.add_vrect(x0=BLACKOUT_START, x1=BLACKOUT_END, fillcolor=MOON_COLOR, opacity=0.75, line_width=1,
                      line_color=MOON_COLOR, layer="above")
        fig.add_annotation(x=BLACKOUT_START + (BLACKOUT_END - BLACKOUT_START) / 2, y=0, yref="paper", yanchor="top",
                           text="<b>Behind the Moon</b>", showarrow=False, font={"size": 11, "color": MOON_COLOR})
    if now is not None:
        # A short mark above the bars: a line through them would hide the Moon blackout.
        fig.add_shape(type="line", x0=now, x1=now, y0=0.94, y1=1, yref="paper", line={"color": "#FF7F0E", "width": 3})
        fig.add_annotation(x=now, y=1, yref="paper", yanchor="bottom", text=now_label, showarrow=False,
                           font={"color": "#E8590C"})
    fig.update_xaxes(type="date")
    fig.update_yaxes(categoryorder="array", categoryarray=list(COMPLEXES)[::-1])
    fig.update_layout(height=240, margin={"l": 0, "r": 0, "t": 20, "b": 22}, barmode="overlay", bargap=0.35)
    fig.update_xaxes(side="bottom", ticklabelstandoff=16)
    return fig, contact.coverage, contact.longest_gap


def _flyby(dsn: pd.DataFrame) -> None:
    """Part 3: the 41 minutes behind the Moon, from NASA's planned window."""
    st.caption("Part 3 · The flyby")
    minutes = duration_text(BLACKOUT_END - BLACKOUT_START)
    st.subheader(f"For {minutes.replace(' min', ' minutes')}, the Moon was in the way")
    explain("environment.flyby")
    in_view = sites_in_view(dsn)
    if in_view:
        names = " and ".join(name for name, _ in in_view)
        elevation = in_view[0][1]
        st.markdown(f"On April 6, {names} had Orion about **{elevation:.0f}°** above the horizon. "
                    "It was pointed the right way, but no signal can pass through the Moon.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Planned loss of signal", f"{BLACKOUT_START:%H:%M} UTC")
    c2.metric("No contact", minutes)
    c3.metric("Planned return of signal", f"{BLACKOUT_END:%H:%M} UTC")
    st.caption("Times are NASA's planned blackout window (6:44 to 7:25 p.m. EDT). NASA's flight log reports the "
               "signal returning around 7:24 p.m. EDT, without an exact time.")


def _now(date_from: datetime, date_to: datetime | None, live: bool) -> datetime | None:
    """The moment 'now' refers to: the simulation's latest tick while live, else the window end."""
    if not live:
        return date_to
    try:
        state = _data.synthetic_state(date_from, None)
    except BackendAPIError:
        return None
    return None if state.empty else state["timestamp_utc"].iloc[-1].to_pydatetime()


@st.fragment(run_every=REFRESH_INTERVAL if live else None)
def render(date_from, date_to, live):
    try:
        goes = _data.goes_protons(date_from, date_to)
        events = _data.donki_events(date_from, date_to)
        dsn = _data.dsn_geometry(date_from, date_to)
        orion = _data.real_orion(date_from, None)
        flight_goes = _data.goes_protons(MISSION_START, MISSION_END)
        flight_dsn = _data.dsn_geometry(MISSION_START, MISSION_END)
    except BackendAPIError as e:
        st.error(str(e))
        return
    now = _now(date_from, date_to, live)

    _answers(flight_goes, flight_dsn)

    st.caption("Part 1 · The Sun")
    st.subheader("Solar particles around Earth")
    explain("environment.particles")
    if goes.empty:
        st.info("No GOES particle data in this time range. Run the iswa_goes_protons ingest.")
    else:
        flight_end = orion["timestamp_utc"].max() if not orion.empty else goes["time"].max()
        plot(_particles_chart(goes, events, flight_end))
        if not events.empty:
            with st.expander(f"List of the {len(events)} solar events"):
                table = events.assign(what=events["event_type"].map(EVENT_NAMES).fillna(events["event_type"]))
                st.dataframe(table[["when", "what", "event_id"]].rename(
                    columns={"when": "Time (UTC)", "what": "Event", "event_id": "NASA DONKI id"}),
                    width="stretch", hide_index=True)

    st.caption("Part 2 · The three antennas")
    st.subheader("Can we talk to Orion?")
    explain("environment.contact_now")
    if dsn.empty:
        st.info("No antenna data in this time range. Run the jpl_dsn_geometry ingest.")
    else:
        if now is not None:
            _contact_now(dsn, now)

        st.subheader("Contact windows")
        explain("environment.windows")
        fig, coverage, longest = _windows_chart(dsn, now, "Now" if live else "End of selected time")
        st.caption(f"In this time range, at least one site could reach Orion **{coverage:.0%}** of the time. "
                   f"Longest stretch with no contact: **{duration_text(longest)}** (red bands).")
        plot(fig)

    _flyby(flight_dsn)


render(date_from, date_to, live)
