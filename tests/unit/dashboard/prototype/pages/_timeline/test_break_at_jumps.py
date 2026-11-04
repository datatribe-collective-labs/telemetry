import pandas as pd

from dashboard.src.prototype.pages._timeline import break_at_jumps

T0 = pd.Timestamp("2026-04-05 00:00", tz="UTC")


def frame(*minutes):
    return pd.DataFrame({
        "timestamp_utc": [T0 + pd.Timedelta(minutes=m) for m in minutes],
        "value": [float(m) for m in minutes],
    })


def test_break_at_jumps_inserts_a_blank_row_at_each_jump():
    out = break_at_jumps(frame(0, 1, 30, 31))
    assert len(out) == 5
    assert out["value"].isna().sum() == 1
    assert pd.isna(out.loc[2, "timestamp_utc"])


def test_break_at_jumps_keeps_the_timestamp_column_tz_aware():
    out = break_at_jumps(frame(0, 30))
    assert out["timestamp_utc"].dt.tz is not None


def test_break_at_jumps_leaves_continuous_data_unchanged():
    df = frame(0, 1, 2)
    assert break_at_jumps(df) is df
