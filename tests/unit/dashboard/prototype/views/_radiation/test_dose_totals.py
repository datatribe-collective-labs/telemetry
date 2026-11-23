import pytest

from dashboard.src.prototype.views._radiation import dose_totals


def test_dose_totals_splits_the_final_dose_by_source(journey):
    out = dose_totals(journey(("INNER_BELT", 2, 1e-4), ("DEEP_SPACE", 10, 1e-6)))
    assert out.total_mgy == pytest.approx(2.1)
    assert out.belts_mgy == pytest.approx(2.0)
    assert out.cosmic_mgy == pytest.approx(0.1)


def test_dose_totals_converts_the_peak_to_microgray_per_minute(journey):
    df = journey(("DEEP_SPACE", 2, 1e-6)).assign(total_dose_rate_rad_s=[1e-6, 4.786e-4])
    assert dose_totals(df).peak_ugy_min == pytest.approx(287.16)
