import re

from backend.models import Base
from sqlalchemy import DateTime

# Synthetic tables follow strict conventions
SYNTHETIC_TABLES = {
    "state_snapshot",
    "thermal_output",
    "power_output",
    "comms_output",
    "radiation_output",
    "cross_model_state",
    "telemetry_packet",
    "anomaly_events",
    "ml_feature_vectors",
}

# Real-data tables (JPL/NASA managed) have different conventions
REAL_DATA_TABLES = {
    "close_approaches",
    "orion_ephemeris",
    "donki_events",
    "goes_integral_protons",
    "dsn_site_geometry",
}

ALL_TABLES = SYNTHETIC_TABLES | REAL_DATA_TABLES


def test_schema_conventions():
    # All expected tables present
    assert set(Base.metadata.tables) == ALL_TABLES

    for table in Base.metadata.tables.values():
        if table.name in SYNTHETIC_TABLES:
            # Synthetic tables: lowercase snake_case columns, timestamp_utc PK
            assert all(re.fullmatch(r"[a-z][a-z0-9_]*", c.name) for c in table.columns)
            ts = table.c.timestamp_utc
            assert isinstance(ts.type, DateTime) and ts.type.timezone
            assert ts.primary_key
        elif table.name in REAL_DATA_TABLES:
            # Real-data tables: verify they exist and have PKs, but don't enforce synthetic conventions
            # They use Text, JSONB, composite PKs, and mixed case column names
            pk_cols = [c for c in table.columns if c.primary_key]
            assert len(pk_cols) >= 1, f"Table {table.name} must have at least one PK column"
        else:
            raise AssertionError(f"Unexpected table in metadata: {table.name}")
