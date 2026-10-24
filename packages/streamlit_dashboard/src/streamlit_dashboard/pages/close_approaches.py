"""Close-Approach Data page.

Reads the `close_approaches` table populated by `pipelines.ingest.jpl_cad`.
"""

from datetime import UTC, datetime, timedelta

import plotly.express as px
import streamlit as st

from streamlit_dashboard.data.close_approaches import load_close_approaches
from streamlit_dashboard.data.engine import get_engine

st.title("JPL Close-Approach Data")
st.caption("Near-Earth object close approaches, ingested from the JPL SSD CAD API.")

with st.sidebar:
    st.header("Filters")
    today = datetime.now(UTC).date()
    date_from, date_to = st.date_input(
        "Date range",
        value=(today, today + timedelta(days=60)),
    )
    dist_max_au = st.slider("Max distance (AU)", min_value=0.001, max_value=1.0, value=0.05, step=0.001)
    designation = st.text_input("Designation contains", value="").strip() or None

engine = get_engine()
df = load_close_approaches(engine, date_from, date_to, dist_max_au, designation)

if df.empty:
    st.info("No close approaches match the current filters.")
else:
    col1, col2, col3 = st.columns(3)
    col1.metric("Approaches in view", len(df))
    closest = df.loc[df["dist_au"].idxmin()]
    col2.metric("Closest approach (AU)", f"{closest['dist_au']:.5f}")
    col3.metric("Closest object", closest["des"])

    display_columns = {
        "des": "Designation",
        "close_approach_time": "Close approach (UTC)",
        "dist_au": "Distance (AU)",
        "v_rel_kms": "Rel. velocity (km/s)",
        "h_mag": "H magnitude",
        "body": "Body",
    }
    st.dataframe(
        df[list(display_columns)].rename(columns=display_columns),
        width="stretch",
        hide_index=True,
    )

    fig = px.scatter(
        df,
        x="close_approach_time",
        y="dist_au",
        color="v_rel_kms",
        color_continuous_scale="Blues",
        hover_data=["des", "orbit_id", "h_mag"],
        labels={
            "close_approach_time": "Close approach (UTC)",
            "dist_au": "Distance (AU)",
            "v_rel_kms": "Rel. velocity (km/s)",
        },
        title="Close approach distance over time",
    )
    fig.update_traces(marker={"size": 9, "line": {"width": 0}})
    fig.update_layout(margin={"l": 0, "r": 0, "t": 40, "b": 0})
    st.plotly_chart(fig, width="stretch")
