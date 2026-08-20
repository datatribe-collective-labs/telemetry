from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy import text


@st.cache_data(ttl=60)
def load_close_approaches(
    _engine,
    date_from: date,
    date_to: date,
    dist_max_au: float,
    designation: str | None = None,
) -> pd.DataFrame:
    conditions = [
        "close_approach_time >= :date_from",
        "close_approach_time < :date_to",
        "dist_au <= :dist_max_au",
    ]
    params: dict[str, object] = {
        "date_from": date_from,
        "date_to": date_to,
        "dist_max_au": dist_max_au,
    }
    if designation:
        conditions.append("des ILIKE :designation")
        params["designation"] = f"%{designation}%"

    query = f"""
        SELECT des, orbit_id, close_approach_time, dist_au, dist_min_au,
               dist_max_au, v_rel_kms, v_inf_kms, h_mag, body
        FROM close_approaches
        WHERE {' AND '.join(conditions)}
        ORDER BY close_approach_time
    """
    with _engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)
