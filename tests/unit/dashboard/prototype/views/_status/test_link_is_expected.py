import pytest

from dashboard.src.prototype.views._status import link_is_expected


@pytest.mark.parametrize("reason", ["OUT_OF_DSN_VIEW", "MOON_BLOCKED"])
def test_link_is_expected_for_gaps_caused_by_position(reason):
    assert link_is_expected("NO_LINK", reason)


@pytest.mark.parametrize(("state", "reason"), [
    ("NO_LINK", "NO_POWER"), ("NO_LINK", "LINK_BUDGET"), ("NO_LINK", None), ("NOMINAL", "NONE"),
])
def test_link_is_expected_is_false_otherwise(state, reason):
    assert not link_is_expected(state, reason)
