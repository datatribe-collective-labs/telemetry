"""Shared mission constants and the one sidebar every page uses.

`app.py` calls `sidebar()` before running the selected page, so the Live toggle
and the mission-time slider keep their values while the viewer switches pages.
Pages read the current choice with `time_window()`.
"""

from datetime import UTC, datetime, timedelta

import streamlit as st

LIFTOFF = datetime(2026, 4, 1, 22, 35, tzinfo=UTC)
# Slider bounds: the hour of liftoff to the end of the real (NASA/JPL) data.
MISSION_START = datetime(2026, 4, 1, 22, 0, tzinfo=UTC)
MISSION_END = datetime(2026, 4, 11, 0, 0, tzinfo=UTC)

LIVE_KEY = "live"
WINDOW_KEY = "mission_window"


def sidebar() -> None:
    """Live toggle, plus a mission-time range slider when Live is off."""
    st.toggle(
        "Live",
        value=True,
        key=LIVE_KEY,
        help="Follow the simulation as it runs; pages refresh every 5 seconds. "
        "Turn off to look at a chosen part of the mission.",
    )
    if st.session_state[LIVE_KEY]:
        st.caption("Showing the mission up to the simulation's latest moment.")
        return
    # The slider works on naive datetimes; they are UTC throughout.
    st.slider(
        "Mission time (UTC)",
        min_value=MISSION_START.replace(tzinfo=None),
        max_value=MISSION_END.replace(tzinfo=None),
        value=(MISSION_START.replace(tzinfo=None), MISSION_END.replace(tzinfo=None)),
        step=timedelta(hours=1),
        format="MMM D, HH:mm",
        key=WINDOW_KEY,
    )


def time_window() -> tuple[datetime, datetime | None, bool]:
    """(date_from, date_to, live). While live, date_to is None so new rows are never cut off."""
    if st.session_state.get(LIVE_KEY, True):
        return MISSION_START, None, True
    start, end = st.session_state.get(
        WINDOW_KEY, (MISSION_START.replace(tzinfo=None), MISSION_END.replace(tzinfo=None))
    )
    return start.replace(tzinfo=UTC), end.replace(tzinfo=UTC), False


def mission_day(t: datetime) -> int:
    """Flight day number, counting liftoff day as day 1."""
    return (t - LIFTOFF).days + 1


def mission_clock(t: datetime) -> str:
    """Time since liftoff as e.g. '2 d 03:04:05' ('00:00:43' on day 1)."""
    seconds = max(0, int((t - LIFTOFF).total_seconds()))
    days, rest = divmod(seconds, 86_400)
    clock = f"{rest // 3600:02d}:{rest % 3600 // 60:02d}:{rest % 60:02d}"
    return f"{days} d {clock}" if days else clock
