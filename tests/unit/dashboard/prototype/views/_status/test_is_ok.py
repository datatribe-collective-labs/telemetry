from dashboard.src.prototype.views._status import is_ok


def test_is_ok_is_true_only_for_nominal():
    assert is_ok("NOMINAL")
    assert not is_ok("BATTERY_DISCHARGE")
