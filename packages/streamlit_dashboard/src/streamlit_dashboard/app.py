"""JPL data-source dashboard entrypoint.

Independent prototype dashboard for exploring JPL SSD API datasets - not the
planned TypeScript/Superset spacecraft-telemetry dashboard described in the
ODCS contracts. Each data source gets its own page under `pages/`.

Run: streamlit run src/streamlit_dashboard/app.py
"""

import streamlit as st

st.set_page_config(page_title="Telemetry Project", page_icon="\U0001F4E1", layout="wide")

pages = [
    st.Page("pages/welcome.py", title="Welcome", icon="\U0001F3E0", default=True),
    st.Page("pages/close_approaches.py", title="Close Approaches", icon="\U0001F6F0"),
]

pg = st.navigation(pages)
pg.run()
