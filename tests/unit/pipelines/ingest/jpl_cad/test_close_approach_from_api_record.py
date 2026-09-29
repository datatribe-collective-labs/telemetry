"""Unit tests for pipelines.ingest.jpl_cad.CloseApproach.from_api_record."""

from pipelines.ingest.jpl_cad import CloseApproach


def test_close_approach_from_api_record_maps_all_fields(complete_record, make_close_approach):
    result = CloseApproach.from_api_record(complete_record, default_body="Earth")

    assert result == make_close_approach()


def test_close_approach_from_api_record_sets_missing_optional_fields_to_none(sparse_record):
    result = CloseApproach.from_api_record(sparse_record, default_body="Earth")

    assert result.dist_min_au is None
    assert result.dist_max_au is None
    assert result.v_inf_kms is None
    assert result.h_mag is None


def test_close_approach_from_api_record_uses_default_body_when_blank(sparse_record):
    result = CloseApproach.from_api_record(sparse_record, default_body="Earth")

    assert result.body == "Earth"
