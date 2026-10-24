"""GOES integral proton flux page.

Reads the `goes_integral_protons` table populated by
`pipelines.ingest.iswa_goes_protons`.
"""

from datetime import date, datetime, time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from streamlit_dashboard.data.engine import get_engine
from streamlit_dashboard.data.iswa_goes_protons import load_goes_integral_protons

# Column -> legend label. Each channel keeps a fixed color, so filtering the
# selection never repaints the remaining channels.
CHANNELS = {
    "p1_pfu": "≥1 MeV",
    "p5_pfu": "≥5 MeV",
    "p10_pfu": "≥10 MeV",
    "p30_pfu": "≥30 MeV",
    "p50_pfu": "≥50 MeV",
    "p60_pfu": "≥60 MeV",
    "p100_pfu": "≥100 MeV",
    "p500_pfu": "≥500 MeV",
}
CHANNEL_COLORS = {
    "p10_pfu": "#2a78d6",
    "p100_pfu": "#eb6834",
    "p1_pfu": "#1baf7a",
    "p5_pfu": "#eda100",
    "p30_pfu": "#e87ba4",
    "p50_pfu": "#008300",
    "p60_pfu": "#4a3aa7",
    "p500_pfu": "#e34948",
}
DEFAULT_CHANNELS = ["p10_pfu", "p100_pfu"]

# Artemis II flight interval (launch -> splashdown), as used in
# docs/integration/sgps_ge10_proton_flux.md.
ARTEMIS_II_START = pd.Timestamp("2026-04-01T22:35:12Z")
ARTEMIS_II_END = pd.Timestamp("2026-04-11T00:07:27Z")

# NOAA Solar Radiation Storm scale, by >=10 MeV integral flux (pfu).
S_SCALE = [(100_000, "S5"), (10_000, "S4"), (1_000, "S3"), (100, "S2"), (10, "S1")]
S_SCALE_TABLE = pd.DataFrame(
    [
        ("S1", "Minor", "≥ 10", "Minor impacts on HF radio in polar regions."),
        ("S2", "Moderate", "≥ 100", "Passengers on high-latitude flights may get elevated dose."),
        ("S3", "Strong", "≥ 1,000", "Radiation hazard advised for astronauts on EVA."),
        ("S4", "Severe", "≥ 10,000", "Unavoidable radiation hazard to astronauts on EVA."),
        ("S5", "Extreme", "≥ 100,000", "Unavoidable high radiation hazard to astronauts."),
    ],
    columns=["Level", "Name", "≥10 MeV flux (pfu)", "Typical effect"],
)


def noaa_s_level(flux_ge10_pfu: float) -> str:
    for threshold, level in S_SCALE:
        if flux_ge10_pfu >= threshold:
            return level
    return "Below S1"


st.title("GOES Proton Flux")
st.markdown(
    "**Was space radiation a threat while Artemis II was flying?** Outside "
    "Earth's protective magnetic field, the Orion crew is exposed to energetic "
    "protons thrown out by the Sun during solar flares and coronal mass "
    "ejections. NOAA's GOES weather satellites count these protons "
    "continuously - this page shows what they saw."
)

with st.expander("How to read this page", expanded=True):
    st.markdown(
        "- **Proton flux** is how many protons pass through a small window "
        "each second. It is measured in **pfu** (*particle flux units*: "
        "protons per cm² per second per steradian). Quiet days sit around "
        "0.1-1 pfu at ≥10 MeV; a big solar storm can push it above 10,000.\n"
        "- **Energy channels.** Each line counts protons *at or above* an "
        "energy: `≥10 MeV` means every proton with at least 10 MeV. Higher "
        "channels are always lower, because fewer protons are that energetic. "
        "In the raw data the columns are named after the threshold - "
        "`p1_pfu` is the ≥1 MeV flux in pfu, `p10_pfu` the ≥10 MeV flux, "
        "and so on.\n"
        "- **Why energy matters.** Low-energy protons (≥1-5 MeV) are stopped "
        "by a spacecraft hull. **≥10 MeV** is the standard NOAA uses to "
        "declare a radiation storm. **≥100 MeV** protons go through "
        "shielding and deliver dose to the crew, and ≥500 MeV ones are rare "
        "and come only from the strongest events.\n"
        "- **Log scale.** The y-axis jumps by factors of 10, so a line rising "
        "one grid step means ten times more protons."
    )

with st.sidebar:
    st.header("Filters")
    default_start = date(2026, 4, 1)
    default_stop = date(2026, 4, 11)
    date_range = st.date_input(
        "Date range (UTC)",
        value=(default_start, default_stop),
        help="Defaults to the Artemis II flight (1-11 April 2026).",
    )
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        date_from = datetime.combine(date_range[0], time.min)
        date_to = datetime.combine(date_range[1], time.max)
    else:
        date_from = datetime.combine(default_start, time.min)
        date_to = datetime.combine(default_stop, time.max)
    selected = st.multiselect(
        "Energy channels",
        options=list(CHANNELS),
        default=DEFAULT_CHANNELS,
        format_func=CHANNELS.get,
        help=(
            "Protons at or above each energy. ≥10 MeV sets the NOAA storm "
            "level; ≥100 MeV is the most relevant to crew dose."
        ),
    )

engine = get_engine()
df = load_goes_integral_protons(engine, date_from, date_to)

if df.empty:
    st.warning("No GOES proton records found for the selected date range.")
    st.info(
        "Run `uv run --package pipelines python -m pipelines.ingest.iswa_goes_protons` "
        "to ingest GOES proton flux."
    )
    st.stop()

ge10 = df["p10_pfu"].dropna()
ge100 = df["p100_pfu"].dropna()

st.subheader("At a glance")
if ge10.empty:
    st.info("No ≥10 MeV measurements in this range, so no storm level can be given.")
else:
    peak_idx = ge10.idxmax()
    peak = ge10[peak_idx]
    level = noaa_s_level(peak)
    peak_time = df.loc[peak_idx, "time"]
    if level == "Below S1":
        # ~1 pfu and up is a visible enhancement above background.
        headline = "Elevated, but no storm." if peak >= 1 else "Quiet conditions."
        st.success(
            f"**{headline}** The ≥10 MeV flux peaked at **{peak:.2f} pfu** "
            f"on {peak_time:%d %b %H:%M} UTC, below the 10 pfu radiation-storm "
            "threshold. GOES saw no solar radiation storm in this period."
        )
    else:
        storm_samples = int((ge10 >= 10).sum())
        st.warning(
            f"**Solar radiation storm: {level}.** The ≥10 MeV flux peaked at "
            f"**{peak:,.0f} pfu** on {peak_time:%d %b %H:%M} UTC. It stayed above "
            f"the 10 pfu storm threshold for about {storm_samples * 5 / 60:.1f} "
            "hours in this period."
        )

col1, col2, col3, col4 = st.columns(4)
if ge10.empty:
    col1.metric("Peak ≥10 MeV", "n/a")
    col2.metric("NOAA storm level", "n/a")
else:
    col1.metric(
        "Peak ≥10 MeV",
        f"{peak:.2f} pfu",
        help=f"Highest ≥10 MeV flux, at {peak_time:%Y-%m-%d %H:%M} UTC.",
    )
    col2.metric(
        "NOAA storm level",
        level,
        help="NOAA S-scale from the peak ≥10 MeV flux. S1 starts at 10 pfu (see table below).",
    )
col3.metric(
    "Peak ≥100 MeV",
    "n/a" if ge100.empty else f"{ge100.max():.3g} pfu",
    help="Shielding-penetrating protons, the ones that matter most for crew dose.",
)
col4.metric(
    "Measurements",
    f"{len(df):,}",
    help=(
        "5-minute averages from satellite "
        + (", ".join(sorted(df["proton_satellite"].dropna().unique())) or "n/a")
        + "."
    ),
)

st.subheader("Proton flux over time")
st.caption(
    "Spikes are solar particle events. The shaded band is the Artemis II flight; "
    "the dashed line is where NOAA declares a radiation storm."
)
if not selected:
    st.info("Select at least one energy channel.")
else:
    fig = go.Figure()
    for column, channel_name in CHANNELS.items():
        if column not in selected:
            continue
        fig.add_trace(
            go.Scatter(
                x=df["time"],
                y=df[column],
                name=channel_name,
                mode="lines",
                line={"color": CHANNEL_COLORS[column], "width": 2},
                hovertemplate="%{y:.3g} pfu",
            )
        )
    fig.add_vrect(
        x0=ARTEMIS_II_START,
        x1=ARTEMIS_II_END,
        fillcolor="#898781",
        opacity=0.12,
        line_width=0,
        layer="below",
    )
    fig.add_annotation(
        x=ARTEMIS_II_START, xanchor="left",
        y=1, yref="paper", yanchor="top",
        text="Artemis II in flight",
        showarrow=False,
    )
    if "p10_pfu" in selected:
        fig.add_hline(y=10, line={"color": "#898781", "width": 1, "dash": "dash"})
        # Not add_hline(annotation_text=...): on a log axis Plotly places that
        # label at 10**y, which stretches the axis to 1e10.
        fig.add_annotation(
            x=1, xref="paper", xanchor="right",
            y=1, yref="y", yanchor="bottom",  # log axis: y is log10(10 pfu)
            text="Radiation storm threshold (S1: ≥10 MeV at 10 pfu)",
            showarrow=False,
        )
    fig.update_layout(
        yaxis={"type": "log", "title": "Protons / cm² · s · sr (pfu)"},
        xaxis={"title": "Time (UTC)"},
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
    )
    st.plotly_chart(fig, width="stretch")

with st.expander("NOAA Solar Radiation Storm scale"):
    st.dataframe(S_SCALE_TABLE, width="stretch", hide_index=True)
    st.caption("Source: NOAA Space Weather Prediction Center space weather scales.")

st.subheader("Data")
st.caption(
    "Integral proton flux from the primary GOES satellite (5-minute averages), "
    "via the NASA CCMC iSWA HAPI service. This is NOAA's real-time product - "
    "provisional, not the reprocessed science archive. Flux columns are in pfu."
)
st.dataframe(
    df,
    width="stretch",
    hide_index=True,
    column_config={
        "time": st.column_config.DatetimeColumn("Time (UTC)"),
        "proton_satellite": "Satellite",
        **{
            column: st.column_config.NumberColumn(
                f"{label} flux",
                format="%.3g",
                help=f"Protons {label}, in pfu (column `{column}`).",
            )
            for column, label in CHANNELS.items()
        },
        "ingested_at": st.column_config.DatetimeColumn("Ingested at"),
    },
)
