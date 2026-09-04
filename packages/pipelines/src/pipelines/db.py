import os

import psycopg

DEFAULT_DATABASE_URL = "postgresql://telemetry:telemetry@localhost:5433/telemetry"


def get_connection() -> psycopg.Connection:
    database_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    return psycopg.connect(database_url)
