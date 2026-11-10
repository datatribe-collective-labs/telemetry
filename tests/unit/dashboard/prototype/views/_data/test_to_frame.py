from datetime import UTC, datetime

from pydantic import BaseModel

from dashboard.src.prototype.views._data import to_frame


class Row(BaseModel):
    timestamp_utc: datetime
    value: float


def test_to_frame_sorts_by_time_and_drops_duplicate_times():
    t1, t2 = datetime(2026, 4, 5, 1, tzinfo=UTC), datetime(2026, 4, 5, 2, tzinfo=UTC)
    rows = [Row(timestamp_utc=t2, value=2), Row(timestamp_utc=t1, value=1), Row(timestamp_utc=t2, value=2)]
    df = to_frame(rows, "timestamp_utc")
    assert df["value"].tolist() == [1, 2]
    assert df["timestamp_utc"].dt.tz is not None


def test_to_frame_returns_empty_frame_for_no_items():
    assert to_frame([], "timestamp_utc").empty
