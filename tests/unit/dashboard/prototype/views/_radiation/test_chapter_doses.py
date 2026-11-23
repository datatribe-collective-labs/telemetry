import pandas as pd
import pytest

from dashboard.src.prototype.views._radiation import chapter_doses


def full(journey):
    return journey(("OUTER_BELT", 2, 1e-5), ("DEEP_SPACE", 3, 1e-6), ("INNER_BELT", 4, 1e-4), ("DEEP_SPACE", 10, 1e-6),
                   ("OUTER_BELT", 2, 1e-5), ("INNER_BELT", 2, 1e-4))


def test_chapter_doses_add_up_to_the_total(journey):
    df = full(journey)
    out = chapter_doses(df)
    total = df["cumulative_dose_krad"].iloc[-1] * 10_000
    assert out.leaving_mgy + out.quiet_mgy + out.home_mgy == pytest.approx(total)


def test_chapter_doses_keep_early_deep_space_in_the_first_chapter(journey, at):
    out = chapter_doses(full(journey))
    assert out.quiet_start == at(9)
    assert out.leaving_mgy == pytest.approx((2e-5 + 3e-6 + 4e-4) * 10_000)


def test_chapter_doses_starts_coming_home_after_the_last_deep_space_row(journey, at):
    out = chapter_doses(full(journey))
    assert out.home_start == at(19)
    assert out.quiet_mgy == pytest.approx(1e-5 * 10_000)
    assert out.home_mgy == pytest.approx((2e-5 + 2e-4) * 10_000)


def test_chapter_doses_is_none_before_the_return_belts(journey):
    assert chapter_doses(journey(("INNER_BELT", 3, 1e-4), ("DEEP_SPACE", 5, 1e-6))) is None


def test_chapter_doses_is_none_without_an_inner_belt(journey):
    assert chapter_doses(journey(("DEEP_SPACE", 5, 1e-6))) is None


def test_chapter_doses_is_none_before_leaving_the_belts(journey):
    assert chapter_doses(journey(("OUTER_BELT", 2, 1e-5), ("INNER_BELT", 3, 1e-4))) is None


def test_chapter_doses_empty_is_none():
    assert chapter_doses(pd.DataFrame()) is None
