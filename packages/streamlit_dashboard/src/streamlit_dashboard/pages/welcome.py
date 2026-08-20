"""Welcome / landing page for the Telemetry Project dashboard."""

import streamlit as st

st.title("Telemetry Project - Data Tribe \U0001F4E1")

st.markdown(
    "Open-source telemetry project that ingests, processes, and analyzes "
    "mission telemetry data in real-time using publicly available NASA "
    "flight data."
)

st.markdown("**What it provides:**")
st.markdown(
    "- Real-time ingestion and processing of telemetry streams\n"
    "- Storage and analysis of the data\n"
    "- Dashboard for real-time monitoring and visualization"
)