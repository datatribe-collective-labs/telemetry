"""Artemis II Digital Twin Dashboard — Streamlit Prototype v1.

Four pages, written for non-experts first:
  Mission            where is Orion, and is it OK?
  Spacecraft health  temperature, battery, power (synthetic)
  Space environment  solar particles, solar events, antenna contact (real)
  Model accuracy     simulated vs real trajectory (for engineers)

The project's one dashboard (the real-data-only Data Explorer was retired, see
docs/decisions/ONE_DASHBOARD.md). Reads everything through the FastAPI backend, which
must be running at http://localhost:8000.

Run:
    uv run --package dashboard streamlit run dashboard/src/prototype/app.py
"""

import sys
from pathlib import Path

import streamlit as st

# Enable absolute imports used by pages (e.g. `dashboard.src.prototype.data...`)
# regardless of the directory `streamlit run` was launched from.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root

from dashboard.src.prototype.views._controls import sidebar

st.set_page_config(
    page_title="Artemis II Digital Twin",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# The page modules live in `views/`, NOT `pages/`: Streamlit auto-discovers a `pages/`
# folder next to the entry script as old-style multipage pages, so after a server restart
# a deep link like /health would run that file on its own, without this script (no
# sys.path fix above, no navigation) - ModuleNotFoundError: dashboard (#48).
pages = {
    "Artemis II digital twin": [
        st.Page("views/mission.py", title="Mission", icon="🚀", default=True),
        st.Page("views/health.py", title="Spacecraft health", icon="🩺"),
        st.Page("views/environment.py", title="Space environment", icon="☀️"),
    ],
    "For engineers": [
        st.Page("views/accuracy.py", title="Model accuracy", icon="📐"),
    ],
}

pg = st.navigation(pages)
# Rendered on every page, so Live / mission time carry over between pages.
with st.sidebar:
    sidebar()
pg.run()
