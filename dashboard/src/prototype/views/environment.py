"""Space environment page: what is space around Orion like, and can we talk to it?

All real data (NASA/JPL). Replaces the old Space Weather and DSN Coverage pages.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboard.src.prototype.data.backend_api import BackendAPIError
from dashboard.src.prototype.views import _data
from dashboard.src.prototype.views._controls import LIFTOFF, time_window
from dashboard.src.prototype.views._explain import explain
from dashboard.src.prototype.views._live import REFRESH_INTERVAL, plot
from dashboard.src.prototype.views._timeline import true_intervals

# NOAA solar radiation storm scale, defined on the >=10 MeV integral proton flux.
STORM_LEVELS = [(10, 100, "#F2C94C", "Minor storm (S1)"), (100, 1000, "#F2994A", "Moderate storm (S2)"),
                (1000, 1e6, "#EB5757", "Strong storm (S3+)")]
EVENT_NAMES = {
    "CME": "Solar eruption (CME)", "FLR": "Solar flare", "SEP": "Solar particle event",
    "GST": "Geomagnetic storm", "HSS": "Fast solar wind", "IPS": "Shock in the solar wind",
    "RBE": "Radiation belt boost", "MPC": "Magnetopause crossing",
}
# Where each complex is, for readers who don't know the DSN.
COMPLEXES = {"Goldstone": "California, USA", "Madrid": "Spain", "Canberra": "Australia"}
COMPLEX_COLORS = {"Goldstone": "#1F77B4", "Madrid": "#9467BD", "Canberra": "#17BECF"}
DSN_STEP = pd.Timedelta("1h")  # dsn_site_geometry cadence

st.title("Space environment")
st.caption("The space weather Orion flew through, and which of NASA's big antennas could reach it. "
           "All data on this page is real, published by NASA/JPL.")

date_from, date_to, live = time_window()


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
            if r["visible"]:
                st.markdown("### :green[Can reach Orion]")
                st.caption(f"Orion is {r['elevation_deg']:.0f}° above the horizon")
            else:
                st.markdown("### :gray[Out of view]")
                st.caption("Orion is below this site's horizon")


def _windows_chart(dsn: pd.DataFrame, now: datetime | None, now_label: str) -> tuple[go.Figure, float, pd.Timedelta]:
    """Contact windows per complex, plus coverage share and the longest gap with no contact."""
    fig = go.Figure()
    for name in COMPLEXES:
        site = dsn[dsn["complex"] == name]
        for start, end in true_intervals(site["epoch"], site["visible"].fillna(False).astype(bool), max_gap=DSN_STEP):
            fig.add_trace(go.Bar(base=[start], x=[(end - start) / pd.Timedelta("1ms")], y=[name], orientation="h",
                                 marker_color=COMPLEX_COLORS[name], showlegend=False,
                                 hovertemplate=f"{name}<br>{start:%b %d %H:%M} → {end:%b %d %H:%M} UTC<extra></extra>"))
    any_visible = dsn.groupby("epoch")["visible"].any()
    coverage = float(any_visible.mean()) if len(any_visible) else 0.0
    gaps = true_intervals(any_visible.index.to_series(), ~any_visible, max_gap=DSN_STEP)
    longest = max((end - start for start, end in gaps), default=pd.Timedelta(0))
    for start, end in gaps:
        fig.add_vrect(x0=start, x1=end, fillcolor="#EB5757", opacity=0.12, line_width=0, layer="below")
    if now is not None:
        fig.add_vline(x=now, line_color="#FF7F0E", line_width=2, annotation_text=now_label,
                      annotation_position="top")
    fig.update_xaxes(type="date")
    fig.update_yaxes(categoryorder="array", categoryarray=list(COMPLEXES)[::-1])
    fig.update_layout(height=220, margin={"l": 0, "r": 0, "t": 20, "b": 0}, barmode="overlay", bargap=0.35)
    return fig, coverage, longest


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
    except BackendAPIError as e:
        st.error(str(e))
        return
    now = _now(date_from, date_to, live)

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

    st.subheader("Can we talk to Orion?")
    explain("environment.contact_now")
    if dsn.empty:
        st.info("No antenna data in this time range. Run the jpl_dsn_geometry ingest.")
        return
    if now is not None:
        _contact_now(dsn, now)

    st.subheader("Contact windows")
    explain("environment.windows")
    fig, coverage, longest = _windows_chart(dsn, now, "Now" if live else "End of selected time")
    st.caption(f"At least one site could reach Orion **{coverage:.0%}** of the time. "
               f"Longest stretch with no contact: **{longest / pd.Timedelta('1h'):.0f} h** (red bands).")
    plot(fig)


render(date_from, date_to, live)
