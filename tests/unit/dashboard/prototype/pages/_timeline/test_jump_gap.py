import pandas as pd

from dashboard.src.prototype.pages._timeline import MIN_JUMP, jump_gap

T0 = pd.Timestamp("2026-04-02 02:00", tz="UTC")


def every(seconds, n=10):
    return pd.Series([T0 + pd.Timedelta(seconds=seconds * i) for i in range(n)])


def test_jump_gap_is_at_least_two_minutes_for_real_time_ticks():
    assert jump_gap(every(1)) == MIN_JUMP


def test_jump_gap_scales_with_sped_up_ticks():
    # 300x: ticks 5 min apart must not count as jumps.
    assert jump_gap(every(300)) == pd.Timedelta(minutes=25)


def test_jump_gap_falls_back_without_enough_data():
    assert jump_gap(every(1, n=1)) == MIN_JUMP
