"""Cached data access for the pages: every row in the window, as DataFrames.

The backend caps each request at MAX_LIMIT rows, so `fetch_all` pages through
results; without it, long tables (e.g. 3,000+ GOES rows for the mission) were cut
off silently after the first 1,000.
"""

from collections.abc import Callable
from datetime import datetime

import pandas as pd
import streamlit as st

from dashboard.src.prototype.data.backend_api import MAX_LIMIT, get_api
from dashboard.src.prototype.pages._live import CACHE_TTL_S, current_run

# Newest simulated ticks to load (1 Hz, so ~2.8 h of replay). Real tables are small.
MAX_SYNTHETIC_ROWS = 10_000
MAX_REAL_ROWS = 20_000
REAL_TTL_S = 600


def fetch_all(fetch_page: Callable, *, page_size: int = MAX_LIMIT, max_rows: int = MAX_REAL_ROWS, **kwargs) -> list:
    """Call a paged list endpoint until it has returned `total` rows (or `max_rows`)."""
    items: list = []
    while len(items) < max_rows:
        resp = fetch_page(limit=page_size, offset=len(items), **kwargs)
        if resp is None or not resp.items:
            break
        items.extend(resp.items)
        if len(items) >= resp.total:
            break
    return items[:max_rows]


def to_frame(items: list, time_column: str) -> pd.DataFrame:
    """Pydantic items -> DataFrame sorted by a UTC time column, one row per time."""
    if not items:
        return pd.DataFrame()
    df = pd.DataFrame([item.model_dump() for item in items])
    df[time_column] = pd.to_datetime(df[time_column], utc=True)
    return df.drop_duplicates(subset=time_column).sort_values(time_column, ignore_index=True)


def _synthetic(fetch_page: Callable, date_from: datetime, date_to: datetime | None) -> pd.DataFrame:
    # Newest-written first, so the most recent ticks are kept and current_run() can
    # drop rows left behind by an earlier producer run. Rows can repeat across pages
    # while the producer is writing; to_frame() de-duplicates them.
    items = fetch_all(
        fetch_page, max_rows=MAX_SYNTHETIC_ROWS, date_from=date_from, date_to=date_to,
        order="desc", sort_by="ingested_at",
    )
    return to_frame(current_run(items), "timestamp_utc")


@st.cache_data(ttl=CACHE_TTL_S, show_spinner=False)
def synthetic_state(date_from: datetime, date_to: datetime | None) -> pd.DataFrame:
    return _synthetic(get_api().get_synthetic_state, date_from, date_to)


@st.cache_data(ttl=CACHE_TTL_S, show_spinner=False)
def synthetic_thermal(date_from: datetime, date_to: datetime | None) -> pd.DataFrame:
    return _synthetic(get_api().get_synthetic_thermal, date_from, date_to)


@st.cache_data(ttl=CACHE_TTL_S, show_spinner=False)
def synthetic_power(date_from: datetime, date_to: datetime | None) -> pd.DataFrame:
    return _synthetic(get_api().get_synthetic_power, date_from, date_to)


@st.cache_data(ttl=REAL_TTL_S, show_spinner=False)
def real_orion(date_from: datetime, date_to: datetime | None) -> pd.DataFrame:
    df = to_frame(fetch_all(get_api().get_orion_ephemeris, date_from=date_from, date_to=date_to), "epoch")
    return df.rename(columns={"epoch": "timestamp_utc"})


@st.cache_data(ttl=REAL_TTL_S, show_spinner=False)
def moon(date_from: datetime, date_to: datetime | None) -> pd.DataFrame:
    df = to_frame(fetch_all(get_api().get_moon_ephemeris, date_from=date_from, date_to=date_to), "epoch")
    return df.rename(columns={"epoch": "timestamp_utc"})


@st.cache_data(ttl=REAL_TTL_S, show_spinner=False)
def mission_events() -> pd.DataFrame:
    items = get_api().get_mission_events().items
    return pd.DataFrame([item.model_dump() for item in items])


@st.cache_data(ttl=REAL_TTL_S, show_spinner=False)
def goes_protons(date_from: datetime, date_to: datetime | None) -> pd.DataFrame:
    return to_frame(fetch_all(get_api().get_goes_protons, date_from=date_from, date_to=date_to), "time")


@st.cache_data(ttl=REAL_TTL_S, show_spinner=False)
def donki_events(date_from: datetime, date_to: datetime | None) -> pd.DataFrame:
    items = fetch_all(get_api().get_donki_events, date_from=date_from, date_to=date_to)
    if not items:
        return pd.DataFrame()
    # Several events can share a time, so no de-duplication on time here.
    df = pd.DataFrame([item.model_dump() for item in items])
    df["when"] = pd.to_datetime(df["event_time"].fillna(df["start_time"]), utc=True)
    return df.dropna(subset=["when"]).sort_values("when", ignore_index=True)


@st.cache_data(ttl=REAL_TTL_S, show_spinner=False)
def dsn_geometry(date_from: datetime, date_to: datetime | None) -> pd.DataFrame:
    items = fetch_all(get_api().get_dsn_geometry, date_from=date_from, date_to=date_to)
    if not items:
        return pd.DataFrame()
    # One row per site per time, so no de-duplication on time alone.
    df = pd.DataFrame([item.model_dump() for item in items])
    df["epoch"] = pd.to_datetime(df["epoch"], utc=True)
    return df.sort_values(["complex", "epoch"], ignore_index=True)
