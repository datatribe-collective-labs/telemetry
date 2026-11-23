import pytest

from dashboard.src.prototype.views._status import link_status


@pytest.mark.parametrize(("state", "reason", "expected"), [
    ("NOMINAL", "NONE", ("Connected", "green")),
    ("DEGRADED", "NONE", ("Weak signal", "orange")),
    ("NO_LINK", "OUT_OF_DSN_VIEW", ("Out of DSN view", "gray")),
    ("NO_LINK", "MOON_BLOCKED", ("Behind the Moon", "blue")),
    ("NO_LINK", "NO_POWER", ("Radio off: no power", "red")),
    ("NO_LINK", "LINK_BUDGET", ("Signal too weak", "red")),
])
def test_link_status_names_each_state_and_reason(state, reason, expected):
    assert link_status(state, reason) == expected


@pytest.mark.parametrize("reason", [None, float("nan")])
def test_link_status_handles_a_row_without_a_reason(reason):
    assert link_status("NO_LINK", reason) == ("No link", "orange")
