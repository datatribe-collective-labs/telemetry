from dashboard.src.prototype.views._status import POWER_STATUS, THERMAL_STATUS, status


def test_status_translates_known_codes_to_plain_words():
    assert status(THERMAL_STATUS, "COLD_SURVIVAL") == ("Too cold, heater on", "blue")
    assert status(POWER_STATUS, "BATTERY_DISCHARGE") == ("Running on battery", "orange")


def test_status_shows_unknown_codes_readably_in_grey():
    assert status(POWER_STATUS, "SOMETHING_NEW") == ("Something new", "gray")
