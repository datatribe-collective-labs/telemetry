"""Radio link gaps: when Orion had no link, why, and the Mission page's timeline."""

from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go

from dashboard.src.prototype.views._status import LINK_LOSS_STATUS
from dashboard.src.prototype.views._timeline import jump_gap, true_intervals

UNKNOWN_REASON = "UNKNOWN"
CONNECTED_COLOR = "#7BC8A4"
REASON_COLORS = {
    "OUT_OF_DSN_VIEW": "#9AA5B1",
    "MOON_BLOCKED": "#3B5BDB",
    "NO_POWER": "#D62728",
    "LINK_BUDGET": "#E8590C",
    UNKNOWN_REASON: "#F2A541",
}


@dataclass(frozen=True)
class LinkGap:
    reason: str
    start: pd.Timestamp
    end: pd.Timestamp

    @property
    def label(self) -> str:
        return LINK_LOSS_STATUS.get(self.reason, ("No link", ""))[0]


def link_gaps(comms: pd.DataFrame) -> list[LinkGap]:
    """Every lost-link stretch in time order. Rows without a recorded reason are UNKNOWN."""
    if comms.empty:
        return []
    times = comms["timestamp_utc"]
    lost = comms["comm_state"] == "NO_LINK"
    reasons = comms["link_loss_reason"].where(comms["link_loss_reason"].notna(), UNKNOWN_REASON)
    max_gap = jump_gap(times)
    gaps = [
        LinkGap(reason, start, end)
        for reason in reasons[lost].unique()
        for start, end in true_intervals(times, lost & (reasons == reason), max_gap=max_gap)
    ]
    return sorted(gaps, key=lambda g: g.start)


def gap_at(gaps: list[LinkGap], t) -> LinkGap | None:
    """The gap in progress at `t`; where one gap ends as another starts, the later one."""
    return next((g for g in reversed(gaps) if g.start <= t <= g.end), None)


def duration_text(delta: pd.Timedelta) -> str:
    """A duration in plain words, e.g. 'less than a minute', '17 min', '2 h 28 min'."""
    minutes = int(delta.total_seconds() // 60)
    if minutes < 1:
        return "less than a minute"
    hours, rest = divmod(minutes, 60)
    return f"{hours} h {rest} min" if hours else f"{rest} min"


def link_timeline(gaps: list[LinkGap], start, end, now=None) -> go.Figure:
    """One-row strip: connected time, each gap colored by its reason, and a 'Now' line."""
    fig = go.Figure(go.Bar(
        x=[(end - start) / pd.Timedelta("1ms")], base=[start], y=[0], width=0.8, orientation="h",
        marker={"color": CONNECTED_COLOR}, name="Connected", hoverinfo="skip",
    ))
    for reason in dict.fromkeys(g.reason for g in gaps):
        group = [g for g in gaps if g.reason == reason]
        color = REASON_COLORS.get(reason, REASON_COLORS[UNKNOWN_REASON])
        fig.add_trace(go.Bar(
            x=[(g.end - g.start) / pd.Timedelta("1ms") for g in group], base=[g.start for g in group],
            y=[0] * len(group), width=0.8, orientation="h", name=group[0].label,
            marker={"color": color, "line": {"color": color, "width": 1}},  # short gaps stay visible
            hovertext=[f"<b>{g.label}</b><br>{g.start:%b %d %H:%M} – {g.end:%b %d %H:%M} UTC<br>"
                       f"{duration_text(g.end - g.start)}" for g in group],
            hoverinfo="text",
        ))
    if now is not None:
        # A short mark above the bar: a line through it would hide a gap as short as the Moon's.
        fig.add_shape(type="line", x0=now, x1=now, y0=0.9, y1=1, yref="paper", line={"color": "#E8590C", "width": 3})
        fig.add_annotation(x=now, y=1, yref="paper", yanchor="bottom", text="<b>Now</b>", showarrow=False,
                           font={"color": "#E8590C"})
    fig.update_layout(height=150, barmode="overlay", margin={"l": 0, "r": 0, "t": 22, "b": 28},
                      plot_bgcolor="rgba(0,0,0,0)", legend={"orientation": "h", "y": -0.35, "x": 0},
                      xaxis={"type": "date", "tickformat": "%b %d"},
                      yaxis={"visible": False, "range": [-0.5, 0.5], "fixedrange": True})
    return fig
