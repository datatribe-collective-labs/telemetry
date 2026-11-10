from datetime import timedelta
from itertools import pairwise

import pandas as pd

from dashboard.src.prototype.views._controls import LIFTOFF
from dashboard.src.prototype.views._phases import mission_phases

D = 86_400


def test_mission_phases_splits_the_flight_at_the_big_burns(events):
    phases = mission_phases(events)

    assert [p.name for p in phases] == [
        "Earth orbit", "Trip to the Moon", "Lunar flyby", "Trip home", "Entry & splashdown",
    ]
    assert phases[0].start == LIFTOFF
    assert phases[1].start == LIFTOFF + timedelta(seconds=D + 1.6 * 3600)  # TLI burn starts
    assert phases[2].start == LIFTOFF + timedelta(seconds=4 * D + 6 * 3600)  # last OTC ends
    assert phases[3].start == LIFTOFF + timedelta(seconds=6 * D + 4.4 * 3600)  # first RTC starts
    assert phases[4].end == LIFTOFF + timedelta(seconds=9 * D + 2 * 3600)  # end of timeline


def test_mission_phases_are_contiguous(events):
    phases = mission_phases(events)

    assert all(a.end == b.start for a, b in pairwise(phases))


def test_mission_phases_merges_a_phase_whose_burn_is_missing(events):
    phases = mission_phases(events[events["mode"] != "BURN_OTC"])

    assert [p.name for p in phases] == ["Earth orbit", "Trip to the Moon", "Trip home", "Entry & splashdown"]


def test_mission_phases_is_empty_without_events():
    assert mission_phases(pd.DataFrame()) == []
