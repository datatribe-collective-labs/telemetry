"""Read NASA DONKI events from the telemetry database."""

from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy import text


@st.cache_data(ttl=60)
def load_donki_events(
    _engine,
    date_from: date,
    date_to: date,
    event_types: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    conditions = [
        "COALESCE(event_time, start_time) >= :date_from",
        "COALESCE(event_time, start_time) < :date_to",
    ]
    params: dict[str, object] = {
        "date_from": date_from,
        "date_to": date_to,
    }
    if event_types:
        conditions.append("event_type = ANY(:event_types)")
        params["event_types"] = list(event_types)

    query = f"""
        SELECT event_type, event_id, start_time, end_time, event_time,
               fetched_at, source_url, payload
        FROM donki_events
        WHERE {' AND '.join(conditions)}
        ORDER BY COALESCE(event_time, start_time), event_type, event_id
    """
    with _engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)
