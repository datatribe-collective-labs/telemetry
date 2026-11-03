from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from dashboard.src.prototype.pages._live import current_run

LIFTOFF = datetime(2026, 4, 1, 22, 35, tzinfo=UTC)


def rows(*offsets_s):
    """Items in the order the API returns them (newest-written first)."""
    return [SimpleNamespace(timestamp_utc=LIFTOFF + timedelta(seconds=s)) for s in offsets_s]


def test_current_run_keeps_a_single_run_whole():
    items = rows(3, 2, 1, 0)
    assert current_run(items) == items


def test_current_run_drops_an_older_run_that_got_further_into_the_mission():
    # Current run (restarted at liftoff) wrote t=2..0 last; before it, an older run had
    # reached ~5 days in. Those leftover rows must not become the "latest" point.
    items = rows(2, 1, 0, 432_000, 431_999)
    assert current_run(items) == items[:3]


def test_current_run_keeps_earlier_history_after_a_forward_seek():
    # Seeking forward: the older rows are earlier in sim time, so they are still a
    # consistent history and stay (the Trajectory page draws a gap at the jump).
    items = rows(432_001, 432_000, 1, 0)
    assert current_run(items) == items


def test_current_run_empty_is_empty():
    assert current_run([]) == []
