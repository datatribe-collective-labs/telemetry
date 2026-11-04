import pandas as pd
import pytest

from dashboard.src.prototype.pages._trajectory import separation

T0 = pd.Timestamp("2026-04-05 00:00", tz="UTC")


def rows(*entries):
    """(seconds after T0, x, y, z) -> trajectory frame."""
    return pd.DataFrame([
        {"timestamp_utc": T0 + pd.Timedelta(seconds=s), "x_km": x, "y_km": y, "z_km": z}
        for s, x, y, z in entries
    ])


def test_separation_measures_distance_to_the_nearest_simulated_tick():
    real = rows((0, 100_000, 0, 0))
    syn = rows((-10, 0, 0, 0), (2, 100_003, 4, 0))  # nearest is 2 s later, 5 km away
    out = separation(real, syn)
    assert out["separation_km"].tolist() == pytest.approx([5.0])
    assert out["earth_distance_km"].tolist() == pytest.approx([100_000.0])


def test_separation_skips_real_rows_without_a_tick_within_tolerance():
    real = rows((0, 1, 0, 0), (3600, 1, 0, 0))
    syn = rows((10, 1, 0, 0))
    assert len(separation(real, syn)) == 1


def test_separation_is_empty_without_data():
    assert separation(pd.DataFrame(), rows((0, 1, 0, 0))).empty
