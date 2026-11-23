import pytest

from dashboard.src.prototype.views._status import link_needs_attention


@pytest.mark.parametrize(("state", "reason"), [
    ("DEGRADED", "NONE"), ("NO_LINK", "NO_POWER"), ("NO_LINK", "LINK_BUDGET"), ("NO_LINK", None),
])
def test_link_needs_attention_for_real_problems(state, reason):
    assert link_needs_attention(state, reason)


@pytest.mark.parametrize(("state", "reason"), [
    ("NOMINAL", "NONE"), ("NO_LINK", "OUT_OF_DSN_VIEW"), ("NO_LINK", "MOON_BLOCKED"),
])
def test_link_needs_attention_is_false_when_connected_or_expected(state, reason):
    assert not link_needs_attention(state, reason)
