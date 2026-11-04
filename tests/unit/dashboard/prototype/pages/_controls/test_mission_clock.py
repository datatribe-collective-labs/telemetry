from datetime import timedelta

from dashboard.src.prototype.pages._controls import LIFTOFF, mission_clock


def test_mission_clock_shows_hours_minutes_seconds_on_day_one():
    assert mission_clock(LIFTOFF + timedelta(seconds=43)) == "00:00:43"


def test_mission_clock_adds_days_after_the_first_day():
    assert mission_clock(LIFTOFF + timedelta(days=2, hours=3, minutes=4, seconds=5)) == "2 d 03:04:05"


def test_mission_clock_never_goes_negative_before_liftoff():
    assert mission_clock(LIFTOFF - timedelta(minutes=5)) == "00:00:00"
