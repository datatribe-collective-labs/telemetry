import pandas as pd

from dashboard.src.prototype.views._radiation import usable_rows


def test_usable_rows_drops_rows_without_the_new_fields(journey):
    df = journey(("DEEP_SPACE", 3, 1e-6))
    df.loc[0, "cumulative_belt_dose_krad"] = None
    df.loc[1, "radiation_zone"] = None
    assert len(usable_rows(df)) == 1


def test_usable_rows_keeps_complete_rows(journey):
    df = journey(("DEEP_SPACE", 3, 1e-6))
    assert len(usable_rows(df)) == 3


def test_usable_rows_empty_is_empty():
    assert usable_rows(pd.DataFrame()).empty
