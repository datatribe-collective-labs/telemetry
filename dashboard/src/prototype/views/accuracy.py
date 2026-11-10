"""Model accuracy page (for engineers): does the simulated trajectory match reality?"""

import plotly.graph_objects as go
import streamlit as st

from dashboard.src.prototype.data.backend_api import BackendAPIError
from dashboard.src.prototype.views import _data
from dashboard.src.prototype.views._controls import time_window
from dashboard.src.prototype.views._explain import explain
from dashboard.src.prototype.views._live import REFRESH_INTERVAL, plot
from dashboard.src.prototype.views._trajectory import separation

st.title("Model accuracy")
st.caption("For engineers: how closely the digital twin's simulated trajectory follows the real one "
           "published by NASA/JPL. Both use the same Earth-centred frame (EME2000) and UTC time stamps.")

date_from, date_to, live = time_window()


@st.fragment(run_every=REFRESH_INTERVAL if live else None)
def render(date_from, date_to):
    try:
        real = _data.real_orion(date_from, date_to)
        syn = _data.synthetic_state(date_from, date_to)
    except BackendAPIError as e:
        st.error(str(e))
        return

    st.subheader("Distance between simulated and real position")
    explain("accuracy.separation")
    sep = separation(real, syn)
    if sep.empty:
        if real.empty or syn.empty:
            st.info("Needs both the real trajectory (JPL Horizons ingest) and simulated ticks (physics model).")
        else:
            st.info(f"No overlapping times yet: real data covers {real['timestamp_utc'].min():%b %d %H:%M} – "
                    f"{real['timestamp_utc'].max():%b %d %H:%M} UTC (hourly), the simulation "
                    f"{syn['timestamp_utc'].min():%b %d %H:%M} – {syn['timestamp_utc'].max():%b %d %H:%M} UTC.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Times compared", f"{len(sep)}")
        c2.metric("Typical difference (median)", f"{sep['separation_km'].median():,.1f} km")
        c3.metric("Largest difference", f"{sep['separation_km'].max():,.1f} km")
        share = (sep["separation_km"] / sep["earth_distance_km"]).median()
        st.caption(f"The typical difference is **{share:.4%}** of Orion's distance from Earth.")
        fig = go.Figure(go.Scatter(
            x=sep["timestamp_utc"], y=sep["separation_km"], mode="lines+markers",
            line={"color": "#D62728", "width": 2}, marker={"size": 6},
            customdata=sep["earth_distance_km"],
            hovertemplate="%{x|%b %d %H:%M} UTC<br>%{y:,.1f} km apart<br>"
                          "(%{customdata:,.0f} km from Earth)<extra></extra>"))
        fig.update_layout(height=320, margin={"l": 0, "r": 0, "t": 10, "b": 0}, yaxis_title="km apart",
                          yaxis_rangemode="tozero")
        plot(fig)

    st.subheader("Raw data")
    with st.expander(f"Real trajectory, NASA/JPL ({len(real)} rows)"):
        st.dataframe(real, width="stretch", hide_index=True)
    with st.expander(f"Simulated state, newest 500 of {len(syn)} ticks"):
        st.dataframe(syn.tail(500), width="stretch", hide_index=True)


render(date_from, date_to)
