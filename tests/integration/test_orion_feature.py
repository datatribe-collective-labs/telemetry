import os
import unittest

from pipelines.ingest.jpl_orion import (
    ensure_orion_ephemeris_table,
    fetch_orion_ephemeris,
    upsert_orion_ephemeris,
)
from sqlalchemy import create_engine
from streamlit_dashboard.data.orion import load_orion_ephemeris


@unittest.skipUnless(
    os.environ.get("RUN_ORION_TIMESCALE_INTEGRATION") == "1",
    "set RUN_ORION_TIMESCALE_INTEGRATION=1 to run against TimescaleDB",
)
class OrionPipelineIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pipelines.db import get_connection
        from streamlit_dashboard.data.engine import get_database_url

        cls.connection = get_connection()
        cls.engine = create_engine(
            get_database_url().replace("postgresql://", "postgresql+psycopg://", 1)
        )
        ensure_orion_ephemeris_table(cls.connection)

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()
        cls.engine.dispose()

    def test_jpl_fetch_returns_orion_records(self):
        records = fetch_orion_ephemeris()
        self.assertTrue(records, "JPL Horizons returned no Orion ephemeris records")
        self.assertEqual({record.target_id for record in records}, {"-1024"})
        self.assertTrue(all(record.epoch.tzinfo for record in records))
        self.assertTrue(all(record.speed_kms is not None for record in records))
        self.assertEqual(upsert_orion_ephemeris(self.connection, records), len(records))


@unittest.skipUnless(
    os.environ.get("RUN_ORION_TIMESCALE_INTEGRATION") == "1",
    "set RUN_ORION_TIMESCALE_INTEGRATION=1 to run against TimescaleDB",
)
class OrionTimescaleIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pipelines.db import get_connection
        from streamlit_dashboard.data.engine import get_database_url

        cls.connection = get_connection()
        cls.engine = create_engine(
            get_database_url().replace("postgresql://", "postgresql+psycopg://", 1)
        )
        ensure_orion_ephemeris_table(cls.connection)

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()
        cls.engine.dispose()

    def test_real_records_are_persisted(self):
        result = load_orion_ephemeris(
            self.engine,
        )

        self.assertTrue(
            len(result),
            "TimescaleDB contains no Orion records; run the pipeline test first",
        )
        self.assertEqual(set(result["target_id"]), {"-1024"})

    def test_dashboard_reads_filtered_ordered_real_records(self):
        result = load_orion_ephemeris(self.engine, target_id="-1024")

        self.assertTrue(
            len(result),
            "TimescaleDB contains no Orion records; run the pipeline test first",
        )
        self.assertTrue(result["epoch"].is_monotonic_increasing)
        self.assertTrue(result["speed_kms"].notna().all())


if __name__ == "__main__":
    unittest.main()
