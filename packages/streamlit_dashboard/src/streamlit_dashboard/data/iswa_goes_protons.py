"""Read GOES integral proton flux from the telemetry database."""

from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import text


@st.cache_data(ttl=60)
def load_goes_integral_protons(
    _engine,
    date_from: datetime,
    date_to: datetime,
) -> pd.DataFrame:
    query = """
        SELECT time, proton_satellite,
               p1_pfu, p5_pfu, p10_pfu, p30_pfu,
               p50_pfu, p60_pfu, p100_pfu, p500_pfu,
               ingested_at
        FROM goes_integral_protons
        WHERE time >= :date_from AND time <= :date_to
        ORDER BY time
    """
    with _engine.connect() as conn:
        return pd.read_sql(
            text(query), conn, params={"date_from": date_from, "date_to": date_to}
        )
