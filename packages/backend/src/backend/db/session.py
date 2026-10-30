"""Database connection and session management for the backend API."""

import os
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load .env from project root (where docker-compose.yml lives)
# Go up from: backend/src/backend/db/ -> backend/ -> src/ -> backend/ -> packages/ -> telemetry/
load_dotenv(Path(__file__).parents[5] / ".env")


def get_database_url() -> str:
    """Get the database URL from environment variables."""
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


# Create engine
_database_url = get_database_url()
if _database_url.startswith("postgresql://"):
    _database_url = _database_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()