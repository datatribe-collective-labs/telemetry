from datetime import timedelta

from dashboard.src.prototype.pages._controls import LIFTOFF, mission_day


def test_mission_day_counts_liftoff_day_as_day_one():
    assert mission_day(LIFTOFF) == 1
    assert mission_day(LIFTOFF + timedelta(hours=23)) == 1
    assert mission_day(LIFTOFF + timedelta(days=4, minutes=1)) == 5
