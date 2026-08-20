import os

import streamlit as st
from sqlalchemy import create_engine

DEFAULT_DATABASE_URL = "postgresql://telemetry:telemetry@localhost:5433/telemetry"


@st.cache_resource
def get_engine():
    database_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(database_url)
