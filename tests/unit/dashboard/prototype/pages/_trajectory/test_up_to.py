import pandas as pd

from dashboard.src.prototype.pages._trajectory import up_to

T0 = pd.Timestamp("2026-04-02 02:00", tz="UTC")
HOURLY = pd.DataFrame({"timestamp_utc": [T0 + pd.Timedelta(hours=i) for i in range(3)]})


def test_up_to_keeps_rows_at_or_before_the_time():
    assert len(up_to(HOURLY, T0 + pd.Timedelta(hours=1))) == 2


def test_up_to_keeps_everything_without_a_time():
    assert len(up_to(HOURLY, None)) == 3
