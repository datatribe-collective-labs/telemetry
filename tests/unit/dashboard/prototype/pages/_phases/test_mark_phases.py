from datetime import timedelta

import plotly.graph_objects as go

from dashboard.src.prototype.pages._controls import LIFTOFF
from dashboard.src.prototype.pages._phases import mark_phases, mission_phases


def test_mark_phases_only_marks_boundaries_inside_the_data(events):
    phases = mission_phases(events)
    fig = go.Figure()

    # Data spans the flyby only: just the "Trip home" boundary falls inside it.
    mark_phases(fig, phases, LIFTOFF + timedelta(days=5), LIFTOFF + timedelta(days=7))

    assert [a.text for a in fig.layout.annotations] == ["Trip home"]
    assert len(fig.layout.shapes) == 1
