from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from dashboard.src.prototype.pages import _controls
from dashboard.src.prototype.pages._controls import (
    LIVE_KEY,
    MISSION_START,
    WINDOW_KEY,
    time_window,
)


@pytest.fixture
def session(monkeypatch):
    st = MagicMock()
    st.session_state = {}
    monkeypatch.setattr(_controls, "st", st)
    return st.session_state


def test_time_window_is_open_ended_while_live(session):
    session[LIVE_KEY] = True
    assert time_window() == (MISSION_START, None, True)


def test_time_window_defaults_to_live_before_the_sidebar_ran(session):
    assert time_window()[2] is True


def test_time_window_returns_the_slider_range_in_utc_when_not_live(session):
    session[LIVE_KEY] = False
    session[WINDOW_KEY] = (datetime(2026, 4, 3, 0), datetime(2026, 4, 4, 12))
    expected = (datetime(2026, 4, 3, tzinfo=UTC), datetime(2026, 4, 4, 12, tzinfo=UTC), False)
    assert time_window() == expected
