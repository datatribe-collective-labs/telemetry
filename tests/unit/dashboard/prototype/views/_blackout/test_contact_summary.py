import pandas as pd
import pytest

from dashboard.src.prototype.views._blackout import contact_summary


def test_contact_summary_counts_the_blackout_as_no_contact(geometry, hour):
    out = contact_summary(geometry({h: True for h in range(20, 24)}))  # 20:00 to 23:00
    assert out.gaps == [(hour(22, 44), hour(23))]
    assert out.coverage == pytest.approx(1 - 16 / 180)
    assert out.longest_gap == pd.Timedelta("16min")


def test_contact_summary_is_unchanged_away_from_the_blackout(geometry, hour):
    out = contact_summary(geometry({10: True, 11: False, 12: False, 13: True, 14: True}))
    assert out.gaps == [(hour(11), hour(13))]
    assert out.coverage == pytest.approx(0.5)
    assert out.longest_gap == pd.Timedelta("2h")


def test_contact_summary_merges_a_gap_touching_the_blackout(geometry, hour):
    out = contact_summary(geometry({21: True, 22: False, 23: True}))
    assert out.gaps == [(hour(22), hour(23))]


def test_contact_summary_counts_any_site_as_contact(geometry):
    both = pd.concat([geometry({10: True, 11: False, 12: False}),
                      geometry({10: False, 11: True, 12: True}, site="Madrid")])
    assert contact_summary(both).coverage == 1.0


def test_contact_summary_treats_a_missing_flag_as_no_contact(geometry, hour):
    out = contact_summary(geometry({10: True, 11: None, 12: True}))
    assert out.gaps == [(hour(11), hour(12))]


def test_contact_summary_handles_a_single_time(geometry, hour):
    assert contact_summary(geometry({10: True})).coverage == 1.0
    blocked = geometry({10: True}).assign(epoch=hour(23))
    assert contact_summary(blocked).coverage == 0.0


def test_contact_summary_empty_has_no_coverage():
    out = contact_summary(pd.DataFrame())
    assert (out.coverage, out.gaps) == (0.0, [])
