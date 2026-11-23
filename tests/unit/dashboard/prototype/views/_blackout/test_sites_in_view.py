import pandas as pd

from dashboard.src.prototype.views._blackout import sites_in_view


def test_sites_in_view_uses_the_hour_inside_the_blackout(geometry):
    df = geometry({22: False, 23: True})
    assert sites_in_view(df) == [("Canberra", 22.0)]


def test_sites_in_view_ignores_sites_below_the_horizon(geometry):
    df = pd.concat([geometry({23: True}), geometry({23: False}, site="Madrid", elevation=-7.0)])
    assert [name for name, _ in sites_in_view(df)] == ["Canberra"]


def test_sites_in_view_ignores_rows_after_the_blackout(hour, geometry):
    df = geometry({23: True}).assign(epoch=hour(23) + pd.Timedelta(hours=1))
    assert sites_in_view(df) == []


def test_sites_in_view_empty_is_empty():
    assert sites_in_view(pd.DataFrame()) == []
