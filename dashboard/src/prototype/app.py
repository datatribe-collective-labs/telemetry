"""Artemis II Digital Twin Dashboard — Streamlit Prototype v1.

Four pages, written for non-experts first:
  Mission            where is Orion, and is it OK?
  Spacecraft health  temperature, battery, power (synthetic)
  Space environment  solar particles, solar events, antenna contact (real)
  Model accuracy     simulated vs real trajectory (for engineers)

Separate from the Data Explorer in packages/streamlit_dashboard/. Reads everything
through the FastAPI backend, which must be running at http://localhost:8000.

Run:
    uv run streamlit run dashboard/src/prototype/app.py
"""

import sys
from pathlib import Path

import streamlit as st

# Enable absolute imports used by pages (e.g. `dashboard.src.prototype.data...`)
# regardless of the directory `streamlit run` was launched from.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root

from dashboard.src.prototype.pages._controls import sidebar

st.set_page_config(
    page_title="Artemis II Digital Twin",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = {
    "Artemis II digital twin": [
        st.Page("pages/mission.py", title="Mission", icon="🚀", default=True),
        st.Page("pages/health.py", title="Spacecraft health", icon="🩺"),
        st.Page("pages/environment.py", title="Space environment", icon="☀️"),
    ],
    "For engineers": [
        st.Page("pages/accuracy.py", title="Model accuracy", icon="📐"),
    ],
}

pg = st.navigation(pages)
# Rendered on every page, so Live / mission time carry over between pages.
with st.sidebar:
    sidebar()
pg.run()
