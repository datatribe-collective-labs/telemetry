import pandas as pd

from dashboard.src.prototype.views._radiation import dose_rate_chart


def long_flight(journey):
    return journey(("DEEP_SPACE", 3000, 1e-6), ("INNER_BELT", 1, 1e-3), ("DEEP_SPACE", 3000, 1e-6))


def test_dose_rate_chart_keeps_a_one_tick_peak(journey):
    df = long_flight(journey)
    fig = dose_rate_chart(df)
    assert len(fig.data[0].x) < len(df)
    assert pd.Series(fig.data[0].y).max() == df["total_dose_rate_rad_s"].max() * 600_000


def test_dose_rate_chart_uses_a_log_axis(journey):
    assert dose_rate_chart(journey(("DEEP_SPACE", 5, 1e-6))).layout.yaxis.type == "log"


def test_dose_rate_chart_labels_small_rates_with_their_real_value(journey):
    axis = dose_rate_chart(journey(("DEEP_SPACE", 5, 1e-6))).layout.yaxis
    assert dict(zip(axis.tickvals, axis.ticktext, strict=True))[0.1] == "0.1"


def test_dose_rate_chart_marks_the_moment_only_when_given(journey, at):
    df = journey(("DEEP_SPACE", 5, 1e-6))
    assert len(dose_rate_chart(df).layout.shapes) == 0
    fig = dose_rate_chart(df, now=at(2))
    assert len(fig.layout.shapes) == 1
    assert "You are here" in fig.layout.annotations[0].text
