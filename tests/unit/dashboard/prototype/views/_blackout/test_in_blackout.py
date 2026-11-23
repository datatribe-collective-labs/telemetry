from dashboard.src.prototype.views._blackout import (
    BLACKOUT_END,
    BLACKOUT_START,
    in_blackout,
)


def test_in_blackout_uses_nasas_planned_window(hour):
    assert BLACKOUT_START == hour(22, 44)
    assert BLACKOUT_END == hour(23, 25)


def test_in_blackout_includes_the_start_and_excludes_the_end(hour):
    assert in_blackout(hour(22, 44))
    assert in_blackout(hour(23, 24))
    assert not in_blackout(hour(23, 25))


def test_in_blackout_is_false_before_it_starts(hour):
    assert not in_blackout(hour(22, 43))
