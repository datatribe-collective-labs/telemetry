from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import text


@st.cache_data(ttl=60)
def load_dsn_site_geometry(
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
        SELECT target_id, site, complex, epoch,
               azimuth_deg, elevation_deg, range_km, range_rate_kms,
               light_time_s, visible
        FROM dsn_site_geometry
        WHERE {' AND '.join(conditions)}
        ORDER BY epoch, site
    """
    with _engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)
