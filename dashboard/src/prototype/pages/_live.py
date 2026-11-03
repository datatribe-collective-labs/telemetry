"""Shared live-refresh helpers for the synthetic-telemetry pages.

Each page renders its data section inside an ``st.fragment`` that reruns every
REFRESH_INTERVAL while "Live" is on, so new replay rows show up without a
full-page rerun (the sidebar keeps its state).
"""

import plotly.graph_objects as go
import streamlit as st

REFRESH_INTERVAL = "5s"
# Kept below REFRESH_INTERVAL so every fragment run sees fresh rows.
CACHE_TTL_S = 2


def live_toggle(key: str) -> bool:
    """Sidebar toggle for live mode (on by default)."""
    return st.toggle(
        "Live (refresh every 5 s)",
        value=True,
        key=key,
        help="Re-fetch the newest rows every 5 s. While live, the end date/time is "
        "ignored so new replay data is never filtered out.",
    )


def current_run(items: list) -> list:
    """Keep the leading items that belong to the producer's current run.

    Expects rows newest-written first (the API client's default: sort_by=ingested_at,
    order=desc). Within one run the simulation clock only moves forward, so walking
    back in write order the timestamps keep decreasing. A timestamp *later* than the
    previous one means we crossed into an older run that had got further into the
    mission (the producer was restarted at an earlier MET), so stop there - otherwise
    that run's leftover rows would plot as the "latest" point.
    """
    kept = []
    for item in items:
        if kept and item.timestamp_utc > kept[-1].timestamp_utc:
            break
        kept.append(item)
    return kept


def plot(fig: go.Figure) -> None:
    """st.plotly_chart with a fixed uirevision, so zoom/pan survive live refreshes."""
    fig.update_layout(uirevision="live")
    st.plotly_chart(fig, width="stretch")
