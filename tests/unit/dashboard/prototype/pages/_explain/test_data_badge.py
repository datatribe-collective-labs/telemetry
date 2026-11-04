import pytest

from dashboard.src.prototype.pages._explain import BADGES, data_badge


def test_data_badge_renders_one_badge_per_source_in_order():
    assert data_badge("real", "synthetic") == f"{BADGES['real']} {BADGES['synthetic']}"


def test_data_badge_returns_empty_string_without_sources():
    assert data_badge() == ""


def test_data_badge_rejects_unknown_source():
    with pytest.raises(KeyError):
        data_badge("made_up")
