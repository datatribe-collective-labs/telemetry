import numpy as np
import pandas as pd

from dashboard.src.prototype.views._timeline import break_at_jumps, thin, true_intervals

T0 = pd.Timestamp("2026-04-02 02:00", tz="UTC")


def mission(n=12_000, skip_at=None):
    """One row a minute, with a smooth value and an optional 3-hour hole in the data."""
    minutes = np.arange(n, dtype=float)
    if skip_at is not None:
        minutes[skip_at:] += 180
    return pd.DataFrame({
        "timestamp_utc": T0 + pd.to_timedelta(minutes, unit="min"),
        "value": np.sin(minutes / 300),
        "state": "NOMINAL",
    })


def test_thin_reduces_the_number_of_points():
    df = mission()
    # At most min + max per bucket, plus the first and last row
    assert len(thin(df, ["value"], max_points=2000)) <= 2002


def test_thin_leaves_small_frames_whole():
    df = mission(n=100)
    assert thin(df, ["value"]).equals(df)


def test_thin_keeps_a_one_tick_peak_and_dip():
    df = mission()
    df.loc[5_001, "value"] = 99.0
    df.loc[7_003, "value"] = -99.0
    out = thin(df, ["value"])
    assert out["value"].max() == 99.0
    assert out["value"].min() == -99.0


def test_thin_keeps_the_first_and_last_row():
    df = mission()
    out = thin(df, ["value"])
    assert out["timestamp_utc"].iloc[0] == df["timestamp_utc"].iloc[0]
    assert out["timestamp_utc"].iloc[-1] == df["timestamp_utc"].iloc[-1]


def test_thin_adds_no_false_line_breaks():
    assert thin(mission(), ["value"])["timestamp_utc"].notna().all()


def test_thin_breaks_the_line_at_a_real_jump():
    df = mission(skip_at=6_000)
    out = thin(df, ["value"])
    blank = np.flatnonzero(out["timestamp_utc"].isna())
    assert len(blank) == 1
    assert out["timestamp_utc"].iloc[blank[0] - 1] == df["timestamp_utc"].iloc[5_999]
    assert out["timestamp_utc"].iloc[blank[0] + 1] == df["timestamp_utc"].iloc[6_000]
    assert break_at_jumps(df)["timestamp_utc"].isna().sum() == 1


def test_thin_keeps_every_state_change_exact():
    df = mission()
    df.loc[3_000:3_040, "state"] = "NO_LINK"  # a short gap, like the Moon blackout
    df.loc[9_000:9_200, "state"] = "NO_LINK"
    out = thin(df, ["value"], flags=("state",))
    full = true_intervals(df["timestamp_utc"], df["state"] == "NO_LINK")
    assert true_intervals(out["timestamp_utc"], out["state"] == "NO_LINK") == full


def test_thin_ignores_an_all_empty_column():
    df = mission().assign(empty=np.nan)
    assert len(thin(df, ["empty", "value"])) <= 2002


def test_thin_does_not_change_the_input():
    df = mission(skip_at=6_000)
    before = df.copy()
    thin(df, ["value"], flags=("state",))
    pd.testing.assert_frame_equal(df, before)
