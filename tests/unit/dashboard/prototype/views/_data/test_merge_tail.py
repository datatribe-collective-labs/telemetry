from types import SimpleNamespace

import pandas as pd

from dashboard.src.prototype.views._data import HISTORY_TTL_S, TAIL_ROWS, merge_tail

T0 = pd.Timestamp("2026-04-02 02:00", tz="UTC")


def at(minute):
    return T0 + pd.Timedelta(minutes=minute)


def history(*minutes, value=1.0):
    return pd.DataFrame({"timestamp_utc": [at(m) for m in minutes], "value": [value] * len(minutes)})


def tail(*minutes, value=2.0):
    """Items as the API returns them: newest-written first."""
    return [SimpleNamespace(timestamp_utc=at(m), value=value,
                            model_dump=lambda m=m: {"timestamp_utc": at(m), "value": value})
            for m in minutes]


def test_merge_tail_adds_new_rows_after_history():
    out = merge_tail(history(0, 1, 2), tail(4, 3))
    assert list(out["timestamp_utc"]) == [at(m) for m in (0, 1, 2, 3, 4)]


def test_merge_tail_prefers_the_tail_where_they_overlap():
    out = merge_tail(history(0, 1, 2), tail(2, 1))
    assert list(out["value"]) == [1.0, 2.0, 2.0]


def test_merge_tail_hides_rows_left_by_the_previous_loop():
    # The replay looped and is at minute 2; minutes 3-5 are still last loop's rows.
    out = merge_tail(history(0, 1, 2, 3, 4, 5), tail(2, 1, 0))
    assert out["timestamp_utc"].max() == at(2)


def test_merge_tail_ignores_older_run_rows_in_the_tail():
    # Written just before the loop restarted: later sim time, older write.
    out = merge_tail(history(0, 1), tail(1, 0, 500))
    assert out["timestamp_utc"].max() == at(1)


def test_merge_tail_without_history_returns_the_tail():
    out = merge_tail(pd.DataFrame(), tail(1, 0))
    assert list(out["timestamp_utc"]) == [at(0), at(1)]


def test_merge_tail_without_new_rows_is_empty():
    assert merge_tail(history(0, 1), []).empty


def test_merge_tail_window_covers_the_history_refresh():
    # At 1 tick/s, a shorter tail would leave a hole until history reloads.
    assert TAIL_ROWS > HISTORY_TTL_S
