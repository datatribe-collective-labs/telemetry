import os
import unittest

from pipelines.ingest.jpl_orion import (
    ensure_orion_ephemeris_table,
    fetch_orion_ephemeris,
    upsert_orion_ephemeris,
)

SKIP_REASON = "set RUN_ORION_TIMESCALE_INTEGRATION=1 to run against TimescaleDB"
RUN = os.environ.get("RUN_ORION_TIMESCALE_INTEGRATION") == "1"


class _OrionDatabaseTestCase(unittest.TestCase):
    """Opens one pipelines connection and makes sure the Orion table exists."""

    @classmethod
    def setUpClass(cls):
        from pipelines.db import get_connection

        cls.connection = get_connection()
        ensure_orion_ephemeris_table(cls.connection)

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()

    def read_orion_rows(self, target_id: str = "-1024") -> list[tuple]:
        """(target_id, epoch, speed_kms) rows in epoch order, as the backend serves them."""
        with self.connection.cursor() as cur:
            cur.execute(
                "SELECT target_id, epoch, speed_kms FROM orion_ephemeris"
                " WHERE target_id = %s ORDER BY epoch",
                (target_id,),
            )
            return cur.fetchall()


@unittest.skipUnless(RUN, SKIP_REASON)
class OrionPipelineIntegrationTests(_OrionDatabaseTestCase):
    def test_jpl_fetch_returns_orion_records(self):
        records = fetch_orion_ephemeris()
        self.assertTrue(records, "JPL Horizons returned no Orion ephemeris records")
        self.assertEqual({record.target_id for record in records}, {"-1024"})
        self.assertTrue(all(record.epoch.tzinfo for record in records))
        self.assertTrue(all(record.speed_kms is not None for record in records))
        self.assertEqual(upsert_orion_ephemeris(self.connection, records), len(records))


@unittest.skipUnless(RUN, SKIP_REASON)
class OrionTimescaleIntegrationTests(_OrionDatabaseTestCase):
    def test_real_records_are_persisted(self):
        rows = self.read_orion_rows()

        self.assertTrue(rows, "TimescaleDB contains no Orion records; run the pipeline test first")
        self.assertEqual({row[0] for row in rows}, {"-1024"})

    def test_stored_records_are_ordered_and_complete(self):
        rows = self.read_orion_rows()

        self.assertTrue(rows, "TimescaleDB contains no Orion records; run the pipeline test first")
        epochs = [row[1] for row in rows]
        self.assertEqual(epochs, sorted(epochs))
        self.assertTrue(all(row[2] is not None for row in rows))


if __name__ == "__main__":
    unittest.main()
