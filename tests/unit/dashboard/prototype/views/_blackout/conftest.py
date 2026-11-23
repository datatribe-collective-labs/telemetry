import pandas as pd
import pytest


@pytest.fixture
def hour():
    """A UTC time on April 6, e.g. hour(22, 44)."""
    return lambda h, m=0: pd.Timestamp("2026-04-06", tz="UTC") + pd.Timedelta(hours=h, minutes=m)


@pytest.fixture
def geometry(hour):
    """Hourly rows for one site: {hour: visible}."""

    def build(visible, site="Canberra", elevation=22.0):
        return pd.DataFrame([
            {"epoch": hour(h), "complex": site, "visible": v, "elevation_deg": elevation}
            for h, v in visible.items()
        ])

    return build
