from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import text


@st.cache_data(ttl=60)
def load_orion_ephemeris(
    _engine,
    date_from: datetime | str | None = None,
    date_to: datetime | str | None = None,
    target_id: str = "-1024",
) -> pd.DataFrame:
    conditions = ["target_id = :target_id"]
    params: dict[str, object] = {"target_id": target_id}

    if date_from:
        conditions.append("epoch >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append("epoch <= :date_to")
        params["date_to"] = date_to

    query = f"""
        SELECT target_id, epoch, jd, x_km, y_km, z_km,
               vx_kms, vy_kms, vz_kms, speed_kms,
               light_time_s, range_km, range_rate_kms
        FROM orion_ephemeris
        WHERE {' AND '.join(conditions)}
        ORDER BY epoch
    """
    with _engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)
