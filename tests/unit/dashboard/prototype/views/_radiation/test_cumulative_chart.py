import pandas as pd
import pytest

from dashboard.src.prototype.views._radiation import cumulative_chart


def test_cumulative_chart_stacks_belts_and_cosmic_rays(journey):
    fig = cumulative_chart(journey(("INNER_BELT", 2, 1e-4), ("DEEP_SPACE", 10, 1e-6)))
    assert [t.name for t in fig.data] == ["Radiation belts", "Cosmic rays"]
    assert {t.stackgroup for t in fig.data} == {"dose"}


def test_cumulative_chart_ends_at_the_final_doses(journey):
    fig = cumulative_chart(journey(("INNER_BELT", 2, 1e-4), ("DEEP_SPACE", 10, 1e-6)))
    assert fig.data[0].y[-1] == pytest.approx(2.0)
    assert fig.data[1].y[-1] == pytest.approx(0.1)


def test_cumulative_chart_has_no_blank_rows_at_a_jump(journey, at):
    df = journey(("DEEP_SPACE", 5, 1e-6), ("DEEP_SPACE", 5, 1e-6))
    df.loc[5:, "timestamp_utc"] = df.loc[5:, "timestamp_utc"] + pd.Timedelta(hours=3)
    fig = cumulative_chart(df)
    assert not pd.Series(fig.data[0].x).isna().any()


def test_cumulative_chart_marks_the_moment_when_given(journey, at):
    fig = cumulative_chart(journey(("DEEP_SPACE", 5, 1e-6)), now=at(3), now_label="End of selected time")
    assert "End of selected time" in fig.layout.annotations[0].text
