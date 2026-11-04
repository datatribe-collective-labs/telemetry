"""Mission phases from the planned timeline, for the Mission page's timeline strip and
the phase markers on time-series charts.

The planned timeline (`/mission-events`, ~110 attitude segments keyed by Mission
Elapsed Time) is far too detailed for a viewer, so it is boiled down to five phases
whose boundaries are the big engine burns and the capsule separation:

    Earth orbit -> TLI burn -> Trip to the Moon -> last outbound correction
    -> Lunar flyby -> first return correction -> Trip home -> CM/SM separation
    -> Entry & splashdown

The timeline is a DRAFT extraction from NASA's overview PDF (not yet fact-checked,
see pipelines/ingest/mission_events.py), so phase times are approximate.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go

from dashboard.src.prototype.pages._controls import LIFTOFF

PHASE_COLORS = {
    "Earth orbit": "#9AA5B1",
    "Trip to the Moon": "#5B8FF9",
    "Lunar flyby": "#B37FEB",
    "Trip home": "#5AD8A6",
    "Entry & splashdown": "#F6BD16",
}

# Plain-language names for the segments shown as milestone dots on the strip.
MILESTONES = {
    "BURN_ARB": "Apogee raise burn",
    "BURN_PRB": "Perigee raise burn",
    "BURN_TLI": "Trans-lunar injection: the burn that sends Orion to the Moon",
    "BURN_OTC": "Course correction on the way out",
    "BURN_RTC": "Course correction on the way home",
    "SEP": "Separation",
    "EDL": "Re-entry into Earth's atmosphere",
    "RECOVERY": "Splashdown",
}


@dataclass(frozen=True)
class Phase:
    name: str
    start: datetime
    end: datetime


def met_to_utc(met_s: float) -> datetime:
    """Mission Elapsed Time (seconds since liftoff) -> UTC time."""
    return LIFTOFF + timedelta(seconds=float(met_s))


def mission_phases(events: pd.DataFrame) -> list[Phase]:
    """The five viewer-facing phases, from planned segments (met_start_s, met_end_s, mode).

    A boundary whose burn is missing from the timeline is skipped, so the phase
    before it simply runs on into the next one.
    """
    if events.empty:
        return []
    ev = events.sort_values("met_start_s")

    def first_start(mode, after=-1.0):
        rows = ev[(ev["mode"] == mode) & (ev["met_start_s"] > after)]
        return None if rows.empty else float(rows["met_start_s"].iloc[0])

    tli = first_start("BURN_TLI")
    otc = ev[ev["mode"] == "BURN_OTC"]
    flyby = None if otc.empty else float(otc["met_end_s"].iloc[-1])
    rtc = first_start("BURN_RTC")
    entry = first_start("SEP", after=rtc) if rtc is not None else None

    starts = [("Earth orbit", float(ev["met_start_s"].iloc[0])), ("Trip to the Moon", tli),
              ("Lunar flyby", flyby), ("Trip home", rtc), ("Entry & splashdown", entry)]
    starts = [(name, s) for name, s in starts if s is not None]
    ends = [s for _, s in starts[1:]] + [float(ev["met_end_s"].max())]
    return [Phase(name, met_to_utc(s), met_to_utc(e)) for (name, s), e in zip(starts, ends, strict=True)]


def milestones(events: pd.DataFrame) -> list[tuple[datetime, str]]:
    """(time, plain-language label) for each burn, separation, re-entry and splashdown."""
    if events.empty:
        return []
    rows = events[events["mode"].isin(MILESTONES)].sort_values("met_start_s")
    return [(met_to_utc(r.met_start_s), f"{MILESTONES[r.mode]} ({r.description})") for r in rows.itertuples()]


def phase_at(phases: list[Phase], t: datetime) -> Phase | None:
    """The phase the mission is in at time `t`, or None outside the timeline."""
    return next((p for p in phases if p.start <= t < p.end), None)


def timeline_strip(phases: list[Phase], marks: list[tuple[datetime, str]], now: datetime | None) -> go.Figure:
    """One-row strip of the phases, milestone dots on hover, and a 'now' line."""
    # Numeric y: phase bars on row 0, milestone diamonds on their own row below,
    # so they never cover the phase names.
    fig = go.Figure()
    for p in phases:
        fig.add_trace(go.Bar(
            x=[(p.end - p.start).total_seconds() * 1000], base=[p.start], y=[0], width=0.8, orientation="h",
            marker={"color": PHASE_COLORS.get(p.name, "#9AA5B1")}, name=p.name, text=[p.name],
            textposition="inside", insidetextanchor="middle", textfont={"color": "white", "size": 13},
            hovertemplate=f"<b>{p.name}</b><br>{p.start:%b %d %H:%M} – {p.end:%b %d %H:%M} UTC<extra></extra>",
        ))
    if marks:
        fig.add_trace(go.Scatter(
            x=[t for t, _ in marks], y=[-0.75] * len(marks), mode="markers", name="Milestones",
            marker={"symbol": "diamond", "size": 9, "color": "white", "line": {"color": "#374151", "width": 1}},
            hovertext=[f"{label}<br>{t:%b %d %H:%M} UTC" for t, label in marks], hoverinfo="text",
        ))
    if now is not None:
        fig.add_vline(x=now, line_color="#E8590C", line_width=3)
        fig.add_annotation(x=now, y=1, yref="paper", yanchor="bottom", text="<b>Now</b>", showarrow=False,
                           font={"color": "#E8590C"})
    fig.update_layout(height=150, barmode="overlay", showlegend=False,
                      margin={"l": 0, "r": 0, "t": 22, "b": 28}, plot_bgcolor="rgba(0,0,0,0)",
                      xaxis={"type": "date", "tickformat": "%b %d"},
                      yaxis={"visible": False, "range": [-1.05, 0.45], "fixedrange": True})
    return fig


def mark_phases(fig: go.Figure, phases: list[Phase], t_min, t_max) -> None:
    """Dotted lines where a new phase starts, labelled at the top of the chart.

    Only boundaries inside [t_min, t_max] (the chart's data) are drawn, so the
    markers never stretch the x-axis beyond the data.
    """
    for p in phases[1:]:
        if t_min <= p.start <= t_max:
            fig.add_vline(x=p.start, line_dash="dot", line_color=PHASE_COLORS.get(p.name, "#9AA5B1"), line_width=2)
            fig.add_annotation(x=p.start, y=1, yref="paper", yanchor="top", xanchor="left", text=p.name,
                               showarrow=False, font={"size": 11, "color": "#6B7280"})
