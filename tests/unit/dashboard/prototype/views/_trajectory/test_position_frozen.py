import pandas as pd

from dashboard.src.prototype.views._trajectory import position_frozen

T0 = pd.Timestamp("2026-04-01 22:36", tz="UTC")


def ticks(*positions):
    return pd.DataFrame([
        {"timestamp_utc": T0 + pd.Timedelta(seconds=i), "x_km": x, "y_km": 0.0, "z_km": 0.0}
        for i, x in enumerate(positions)
    ])


def test_position_frozen_when_time_moves_but_position_does_not():
    assert position_frozen(ticks(28_409.0, 28_409.0))


def test_position_frozen_is_false_while_orion_moves():
    assert not position_frozen(ticks(28_409.0, 28_413.0))


def test_position_frozen_is_false_with_too_few_ticks():
    assert not position_frozen(ticks(28_409.0))
