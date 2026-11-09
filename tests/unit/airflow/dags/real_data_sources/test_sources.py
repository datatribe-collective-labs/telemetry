import importlib.util
import pkgutil

import pipelines.ingest


def test_sources_backfill_covers_every_ingest_module(real_data_sources):
    modules = {m.name for m in pkgutil.iter_modules(pipelines.ingest.__path__)}
    assert set(real_data_sources.BACKFILL_SOURCES) == modules


def test_sources_backfill_has_no_duplicates(real_data_sources):
    sources = real_data_sources.BACKFILL_SOURCES
    assert len(sources) == len(set(sources))


def test_sources_backfill_runs_local_files_first(real_data_sources):
    assert real_data_sources.BACKFILL_SOURCES[:2] == ("nasa_oem", "mission_events")


def test_sources_refresh_skips_final_mission_data(real_data_sources):
    assert real_data_sources.REFRESH_SOURCES == ("donki", "iswa_goes_protons", "jpl_cad")


def test_sources_every_source_is_an_importable_module(real_data_sources):
    for source in real_data_sources.BACKFILL_SOURCES:
        assert importlib.util.find_spec(f"pipelines.ingest.{source}") is not None, source
