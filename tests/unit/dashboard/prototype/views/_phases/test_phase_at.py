from datetime import timedelta

from dashboard.src.prototype.views._controls import LIFTOFF
from dashboard.src.prototype.views._phases import mission_phases, phase_at


def test_phase_at_finds_the_lunar_flyby(events):
    phases = mission_phases(events)

    assert phase_at(phases, LIFTOFF + timedelta(days=5)).name == "Lunar flyby"


def test_phase_at_start_boundary_belongs_to_the_new_phase(events):
    phases = mission_phases(events)

    assert phase_at(phases, phases[1].start).name == "Trip to the Moon"


def test_phase_at_is_none_after_the_timeline(events):
    phases = mission_phases(events)

    assert phase_at(phases, phases[-1].end) is None
