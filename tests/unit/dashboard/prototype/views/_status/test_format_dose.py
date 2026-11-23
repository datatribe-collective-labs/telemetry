from dashboard.src.prototype.views._status import format_dose


def test_format_dose_converts_krad_to_mgy():
    assert format_dose(0.001352) == "13.52 mGy"


def test_format_dose_uses_microgray_below_one_mgy():
    assert format_dose(0.00005) == "500 µGy"


def test_format_dose_shows_zero():
    assert format_dose(0.0) == "0 µGy"
