import os
from pathlib import Path
from urllib.parse import quote

import psycopg
from dotenv import load_dotenv

# Load .env from project root (where docker-compose.yml lives)
load_dotenv(Path(__file__).parents[4] / ".env")


def get_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url

    database_values = {
        "POSTGRES_USER": os.environ.get("POSTGRES_USER"),
        "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        "POSTGRES_DB": os.environ.get("POSTGRES_DB"),
    }
    if not all(database_values.values()):
        raise RuntimeError(
            "DATABASE_URL or POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB "
            "must be set"
        )
    return (
        "postgresql://"
        f"{quote(database_values['POSTGRES_USER'], safe='')}:"
        f"{quote(database_values['POSTGRES_PASSWORD'], safe='')}@localhost:5433/"
        f"{quote(database_values['POSTGRES_DB'], safe='')}"
    )


def get_connection() -> psycopg.Connection:
    return psycopg.connect(get_database_url())
