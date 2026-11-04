import pandas as pd

from dashboard.src.prototype.pages._trajectory import at_time

T0 = pd.Timestamp("2026-04-02 02:00", tz="UTC")
HOURLY = pd.DataFrame({"timestamp_utc": [T0 + pd.Timedelta(hours=i) for i in range(3)], "x_km": [1.0, 2.0, 3.0]})


def test_at_time_returns_the_nearest_row():
    assert at_time(HOURLY, T0 + pd.Timedelta(minutes=70))["x_km"] == 2.0


def test_at_time_is_none_outside_the_tolerance():
    assert at_time(HOURLY, T0 - pd.Timedelta(hours=3)) is None


def test_at_time_is_none_for_empty_data_or_no_time():
    assert at_time(pd.DataFrame(), T0) is None
    assert at_time(HOURLY, None) is None
