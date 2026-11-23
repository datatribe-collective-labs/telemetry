import pandas as pd

from dashboard.src.prototype.views._status import storm_summary

T0 = pd.Timestamp("2026-04-02", tz="UTC")


def flux(*values):
    return pd.DataFrame({"time": [T0 + pd.Timedelta(hours=i) for i in range(len(values))], "p10_pfu": values})


def test_storm_summary_is_no_storm_below_the_level():
    out = storm_summary(flux(0.5, 6.57, 1.0), T0)
    assert (out.storm, out.peak_pfu, out.peak_time) == (False, 6.57, T0 + pd.Timedelta(hours=1))


def test_storm_summary_counts_exactly_ten_pfu_as_a_storm():
    assert storm_summary(flux(1.0, 10.0), T0).storm


def test_storm_summary_ignores_times_before_the_start():
    out = storm_summary(flux(50.0, 2.0), T0 + pd.Timedelta(hours=1))
    assert (out.storm, out.peak_pfu) == (False, 2.0)


def test_storm_summary_ignores_missing_values():
    assert storm_summary(flux(None, 3.0), T0).peak_pfu == 3.0


def test_storm_summary_without_data_is_none():
    assert storm_summary(pd.DataFrame(), T0) is None
    assert storm_summary(flux(None), T0) is None
