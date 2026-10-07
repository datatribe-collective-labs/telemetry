"""NASA DONKI event inventory page."""

from datetime import date

import streamlit as st

from streamlit_dashboard.data.donki import load_donki_events
from streamlit_dashboard.data.engine import get_engine

EVENT_TYPES = [
    "CME",
    "CMEAnalysis",
    "SEP",
    "FLR",
    "IPS",
    "GST",
    "RBE",
    "HSS",
    "MPC",
    "WSAEnlilSimulations",
]

st.title("NASA DONKI")
st.caption(
    "NASA CCMC Space Weather Database of Notifications, Knowledge, Information. "
    "The raw DONKI payload is retained in PostgreSQL JSONB."
)

with st.sidebar:
    st.header("Filters")
    date_from = st.date_input("Start date", value=date(2026, 4, 1))
    date_to = st.date_input("End date", value=date(2026, 4, 10))
    selected_types = st.multiselect(
        "Event types",
        options=EVENT_TYPES,
        default=EVENT_TYPES,
    )

if date_to <= date_from:
    st.error("End date must be after start date.")
    st.stop()

engine = get_engine()
df = load_donki_events(engine, date_from, date_to, tuple(selected_types))

if df.empty:
    st.info("No DONKI events match the current filters.")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Events", len(df))
col2.metric("Event types", df["event_type"].nunique())
col3.metric("With event time", int(df["event_time"].notna().sum()))

summary = (
    df.groupby("event_type", dropna=False)
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)
st.subheader("Inventory")
st.dataframe(summary, width="stretch", hide_index=True)

st.subheader("Events")
display = df[
    ["event_type", "event_id", "event_time", "start_time", "end_time", "fetched_at"]
].copy()
st.dataframe(display, width="stretch", hide_index=True)

st.subheader("Raw DONKI record")
selected_event = st.selectbox(
    "Event",
    options=df.index,
    format_func=lambda idx: (
        f"{df.loc[idx, 'event_type']} — {df.loc[idx, 'event_id']}"
    ),
)
row = df.loc[selected_event]
st.caption(row["source_url"])
st.json(row["payload"])
