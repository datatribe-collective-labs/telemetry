"""Artemis II Digital Twin Dashboard — Streamlit Prototype v1.

This is the Digital Twin prototype, separate from the pipeline explorer
in packages/streamlit_dashboard/. This prototype consumes synthetic telemetry
from physics models via the FastAPI backend.

Run:
    uv run --package streamlit_dashboard streamlit run dashboard/src/prototype/app.py

Backend must be running at http://localhost:8000
"""

import sys
from pathlib import Path

import streamlit as st

# Enable absolute imports used by pages (e.g. `dashboard.src.prototype.data...`)
# regardless of the directory `streamlit run` was launched from.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root

st.set_page_config(
    page_title="Artemis II Digital Twin",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Navigation pages
pages = [
    st.Page("pages/overview.py", title="Overview / Health", icon="🏠", default=True),
    st.Page("pages/trajectory.py", title="Trajectory", icon="🛰️"),
    st.Page("pages/thermal.py", title="Thermal", icon="🌡️"),
    st.Page("pages/power.py", title="Power", icon="🔋"),
    st.Page("pages/space_weather.py", title="Space Weather", icon="☀️"),
    st.Page("pages/dsn_coverage.py", title="DSN Coverage", icon="📡"),
]

pg = st.navigation(pages)
pg.run()