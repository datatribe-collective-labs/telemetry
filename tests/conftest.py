"""Fixtures shared by unit and integration tests."""

from datetime import datetime, timezone

import pytest

from pipelines.ingest.jpl_cad import CloseApproach


@pytest.fixture
def make_close_approach():
    """Factory for a valid CloseApproach; pass keyword overrides per test."""

    def _make(**overrides) -> CloseApproach:
        defaults = dict(
            des="2024 AB",
            orbit_id="5",
            close_approach_jd=2460500.5,
            close_approach_time=datetime(2029, 4, 13, 21, 46, tzinfo=timezone.utc),
            dist_au=0.0421,
            dist_min_au=0.0400,
            dist_max_au=0.0450,
            v_rel_kms=12.3,
            v_inf_kms=11.9,
            h_mag=22.1,
            body="Earth",
        )
        defaults.update(overrides)
        return CloseApproach(**defaults)

    return _make
