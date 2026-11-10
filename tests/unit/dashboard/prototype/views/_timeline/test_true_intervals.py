import pandas as pd

from dashboard.src.prototype.views._timeline import true_intervals

T0 = pd.Timestamp("2026-04-05 00:00", tz="UTC")


def times(*minutes):
    return pd.Series([T0 + pd.Timedelta(minutes=m) for m in minutes])


def test_true_intervals_ends_each_span_at_the_next_false_sample():
    spans = true_intervals(times(0, 1, 2, 3, 4), pd.Series([False, True, True, False, False]))
    assert spans == [(T0 + pd.Timedelta(minutes=1), T0 + pd.Timedelta(minutes=3))]


def test_true_intervals_closes_a_span_still_open_at_the_end():
    spans = true_intervals(times(0, 1, 2), pd.Series([False, True, True]))
    assert spans == [(T0 + pd.Timedelta(minutes=1), T0 + pd.Timedelta(minutes=2))]


def test_true_intervals_returns_separate_spans():
    spans = true_intervals(times(0, 1, 2, 3), pd.Series([True, False, True, False]))
    assert len(spans) == 2


def test_true_intervals_cuts_a_span_at_a_time_jump():
    # 2 -> 60 min is a replay jump: the span must not bridge it.
    spans = true_intervals(times(0, 1, 2, 60, 61), pd.Series([True] * 5), max_gap=pd.Timedelta("2min"))
    assert spans == [
        (T0, T0 + pd.Timedelta(minutes=2)),
        (T0 + pd.Timedelta(minutes=60), T0 + pd.Timedelta(minutes=61)),
    ]


def test_true_intervals_returns_nothing_when_never_true():
    assert true_intervals(times(0, 1), pd.Series([False, False])) == []
