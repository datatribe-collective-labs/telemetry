import pytest

from dashboard.src.prototype.views._status import RADIATION_ZONES, radiation_zone


def test_radiation_zone_describes_the_inner_belt():
    label, _, sentence = radiation_zone("INNER_BELT")
    assert label == "Inner belt"
    assert sentence == "Crossing the inner radiation belt."


@pytest.mark.parametrize("zone", ["LOW_EARTH", "INNER_BELT", "OUTER_BELT", "DEEP_SPACE"])
def test_radiation_zone_never_uses_a_warning_color(zone):
    assert radiation_zone(zone)[1] not in {"orange", "red"}


def test_radiation_zone_covers_every_contract_value():
    assert set(RADIATION_ZONES) == {"LOW_EARTH", "INNER_BELT", "OUTER_BELT", "DEEP_SPACE"}


@pytest.mark.parametrize("zone", [None, float("nan")])
def test_radiation_zone_handles_a_row_without_a_zone(zone):
    assert radiation_zone(zone)[0] == "Not available"
