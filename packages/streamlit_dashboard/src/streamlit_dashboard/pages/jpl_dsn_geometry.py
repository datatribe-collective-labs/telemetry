"""Artemis II Orion - DSN ground-station coverage page.

Reads the `dsn_site_geometry` table populated by `pipelines.ingest.jpl_dsn_geometry`
(where Orion sat in each DSN antenna's sky) and tells the story of how the three
Deep Space Network complexes passed Orion between them during the flight.
"""

from datetime import date, datetime, time

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from streamlit_dashboard.data.engine import get_engine
from streamlit_dashboard.data.jpl_dsn_geometry import load_dsn_site_geometry
from streamlit_dashboard.data.orion import load_orion_ephemeris

ELEVATION_CUTOFF_DEG = 10.0
R_EARTH_KM = 6378.137

# One fixed color per complex (categorical slots 1-3), so a site keeps its color
# in every chart. Sites are also always named on-chart, never by color alone.
SITE_LABELS = {
    "Goldstone": "Goldstone, California",
    "Canberra": "Canberra, Australia",
    "Madrid": "Madrid, Spain",
}
SITE_COLORS = {
    "Goldstone, California": "#2a78d6",
    "Canberra, Australia": "#eb6834",
    "Madrid, Spain": "#1baf7a",
}
NO_CONTACT_LABEL = "No site in view"
NO_CONTACT_COLOR = "#d03b3b"
ROW_ORDER = [*SITE_COLORS, NO_CONTACT_LABEL]


def visibility_intervals(df: pd.DataFrame, label_col: str, step: pd.Timedelta) -> pd.DataFrame:
    """Collapse per-epoch `visible` flags into contiguous [start, end) passes per label."""
    rows = []
    for label, group in df.sort_values("epoch").groupby(label_col):
        run_id = (group["visible"] != group["visible"].shift()).cumsum()
        for _, run in group[group["visible"]].groupby(run_id):
            rows.append(
                {
                    label_col: label,
                    "start": run["epoch"].iloc[0],
                    "end": run["epoch"].iloc[-1] + step,
                }
            )
    return pd.DataFrame(rows, columns=[label_col, "start", "end"])


def mark_moment(fig: go.Figure, when: pd.Timestamp, text: str) -> None:
    """Vertical dotted marker with a label (add_vline's annotation breaks on datetimes)."""
    fig.add_shape(
        type="line", x0=when, x1=when, y0=0, y1=1, yref="paper",
        line={"dash": "dot", "width": 1, "color": "#898781"},
    )
    fig.add_annotation(
        x=when, y=1, yref="paper", text=text, showarrow=False,
        yanchor="bottom", font={"size": 12},
    )


def fmt_hours(td: pd.Timedelta) -> str:
    hours = td.total_seconds() / 3600
    return f"{hours:.0f} hour{'s' if round(hours) != 1 else ''}"


# --- Page header -------------------------------------------------------------

st.title("Can Earth hear Orion?")
st.markdown(
    "Orion talks to Earth through NASA's **Deep Space Network (DSN)**: three giant "
    "antenna sites in **California**, **Australia** and **Spain**, spaced about a "
    "third of the way around the globe. As Earth spins, each site can only see Orion "
    "for part of the day, so the sites pass the spacecraft from one to the next "
    "like runners in a relay. This page shows how well that relay covered the "
    "Artemis II flight."
)

with st.sidebar:
    st.header("Coverage Filters")
    default_start = date(2026, 4, 2)
    default_stop = date(2026, 4, 10)

    date_range = st.date_input(
        "Date Range (UTC)",
        value=(default_start, default_stop),
    )
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        date_from = datetime.combine(date_range[0], time.min)
        date_to = datetime.combine(date_range[1], time.max)
    else:
        date_from = datetime.combine(default_start, time.min)
        date_to = datetime.combine(default_stop, time.max)

engine = get_engine()
df = load_dsn_site_geometry(engine, date_from, date_to)

if df.empty:
    st.warning("No DSN site geometry found in TimescaleDB for the selected date range.")
    st.info(
        "Run `uv run --package pipelines python -m pipelines.ingest.jpl_dsn_geometry` "
        "to ingest DSN look angles."
    )
    st.stop()

# --- Derived facts the story is built on ------------------------------------

df["visible"] = df["visible"].fillna(False).astype(bool)
df["label"] = df["complex"].map(SITE_LABELS).fillna(df["complex"])
epochs = df["epoch"].drop_duplicates().sort_values()
step = epochs.diff().median() if len(epochs) > 1 else pd.Timedelta(hours=1)

# Contract 01 `dsn_visibility`: true if at least one complex has Orion in view.
per_epoch = df.groupby("epoch", as_index=False).agg(
    visible=("visible", "any"), light_time_s=("light_time_s", "mean")
)
coverage = per_epoch["visible"].mean()

blackouts = visibility_intervals(
    per_epoch.assign(visible=~per_epoch["visible"], label=NO_CONTACT_LABEL), "label", step
)
blackouts["duration"] = blackouts["end"] - blackouts["start"]
longest = blackouts.loc[blackouts["duration"].idxmax()] if not blackouts.empty else None

farthest = per_epoch.loc[per_epoch["light_time_s"].idxmax()]
site_share = df.groupby("label")["visible"].mean().sort_values(ascending=False)
busiest_site, busiest_share = site_share.index[0], site_share.iloc[0]
span_days = (epochs.iloc[-1] - epochs.iloc[0] + step) / pd.Timedelta(days=1)

# --- Headline ----------------------------------------------------------------

if longest is None:
    gap_sentence = "There was **no moment** when all three sites had lost sight of it."
else:
    gap_sentence = (
        f"There were **{len(blackouts)} gaps** when no site could see it. The "
        f"longest lasted **{fmt_hours(longest['duration'])}**, starting "
        f"{longest['start']:%b %d, %H:%M} UTC."
    )
st.info(
    f"**The short answer:** over these {span_days:.1f} days, at least one site could "
    f"see Orion **{coverage:.0%}** of the time. {gap_sentence}",
    icon="📡",
)

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Time in view", f"{coverage:.0%}",
    help="Share of the time at least one DSN site had Orion "
    f"≥ {ELEVATION_CUTOFF_DEG:.0f}° above its horizon.",
)
col2.metric(
    "Longest gap",
    fmt_hours(longest["duration"]) if longest is not None else "None",
    help=f"Longest stretch with no site in view (resolution: {step}).",
)
col3.metric(
    "Busiest site", busiest_site.split(",")[0],
    help=f"{busiest_site} had Orion in view {busiest_share:.0%} of the time, "
    "more than any other site.",
)
col4.metric(
    "Longest signal delay", f"{farthest['light_time_s']:.2f} s",
    help="One-way radio travel time at Orion's farthest point from Earth.",
)

st.markdown("---")

# --- 1. The relay ------------------------------------------------------------

st.subheader("1 · The relay: which site had Orion, and when")
st.markdown(
    "Each bar is a stretch of time when that site could see Orion. Read the chart "
    "left to right: as one site's bar ends, another's usually begins - that's the "
    "handoff. **Red bars** are the moments when Earth had lost sight of Orion "
    "altogether."
)
passes = pd.concat(
    [visibility_intervals(df, "label", step), blackouts[["label", "start", "end"]]],
    ignore_index=True,
)
if passes.empty:
    st.info("Orion was never above the elevation cutoff in this window.")
else:
    fig_relay = px.timeline(
        passes,
        x_start="start",
        x_end="end",
        y="label",
        color="label",
        color_discrete_map={**SITE_COLORS, NO_CONTACT_LABEL: NO_CONTACT_COLOR},
        category_orders={"label": ROW_ORDER},
    )
    fig_relay.update_traces(
        hovertemplate="<b>%{y}</b><br>%{base|%b %d %H:%M} → %{x|%b %d %H:%M} UTC<extra></extra>"
    )
    fig_relay.update_layout(
        showlegend=False, yaxis_title=None, xaxis_title="Time (UTC)",
        margin={"t": 40}, height=320,
    )
    mark_moment(fig_relay, farthest["epoch"], "Farthest from Earth")
    st.plotly_chart(fig_relay, width="stretch")
    st.caption(
        f"Positions are sampled every {step}, so start and end times are accurate to "
        "about that much."
    )

# --- 2. Why sites come and go ------------------------------------------------

st.subheader("2 · Why each site comes and goes")
st.markdown(
    "From the ground, Orion rises and sets like the Moon. This chart shows **how high "
    "above the horizon** Orion appeared from each site over one day. Below "
    f"{ELEVATION_CUTOFF_DEG:.0f}° (the shaded band) the signal has to cross too much "
    "atmosphere and terrain, so that part of the arc doesn't count as in view."
)
days = sorted(df["epoch"].dt.date.unique())
default_day = farthest["epoch"].date()
day = st.selectbox(
    "Day to zoom in on",
    options=days,
    index=days.index(default_day) if default_day in days else 0,
    format_func=lambda d: f"{d:%a %b %d}" + (" - farthest from Earth" if d == default_day else ""),
)
one_day = df[df["epoch"].dt.date == day]
fig_elev = px.line(
    one_day,
    x="epoch",
    y="elevation_deg",
    color="label",
    color_discrete_map=SITE_COLORS,
    category_orders={"label": list(SITE_COLORS)},
    labels={"epoch": "Time (UTC)", "elevation_deg": "Height above horizon (°)", "label": "Site"},
)
fig_elev.update_traces(
    line={"width": 2},
    hovertemplate="<b>%{fullData.name}</b><br>%{x|%H:%M} UTC: %{y:.0f}°<extra></extra>",
)
fig_elev.add_hrect(
    y0=-90, y1=ELEVATION_CUTOFF_DEG, fillcolor="#898781", opacity=0.12, line_width=0,
)
fig_elev.add_annotation(
    xref="paper", x=0.01, y=ELEVATION_CUTOFF_DEG, text="Too low to count",
    showarrow=False, xanchor="left", yanchor="top", font={"size": 12},
)
fig_elev.update_layout(
    yaxis_range=[-90, 90], hovermode="x unified",
    legend={"orientation": "h", "y": 1.08, "x": 0, "title": None},
)
st.plotly_chart(fig_elev, width="stretch")

# --- 3. Signal delay ---------------------------------------------------------

st.subheader("3 · Talking across 400,000 km")
st.markdown(
    "Radio travels at the speed of light, but at lunar distance even that takes time. "
    "This is how long a message took to get from Orion to the ground. At the farthest "
    f"point it was **{farthest['light_time_s']:.2f} s one way**, so a question from "
    f"Mission Control and the crew's reply needed at least "
    f"**{2 * farthest['light_time_s']:.1f} s** for the round trip."
)
fig_delay = px.line(
    per_epoch,
    x="epoch",
    y="light_time_s",
    labels={"epoch": "Time (UTC)", "light_time_s": "One-way signal delay (s)"},
)
fig_delay.update_traces(
    line={"width": 2, "color": "#2a78d6"},
    hovertemplate="%{x|%b %d %H:%M} UTC: %{y:.2f} s<extra></extra>",
)
fig_delay.add_annotation(
    x=farthest["epoch"], y=farthest["light_time_s"],
    text=f"Farthest: {farthest['light_time_s']:.2f} s", showarrow=True, arrowhead=0, ay=-30,
)
fig_delay.update_layout(hovermode="x")
st.plotly_chart(fig_delay, width="stretch")

# --- Fine print --------------------------------------------------------------

with st.expander("About this data and its limits"):
    st.markdown(
        f"""
- **Source:** JPL Horizons, which predicts where Orion (spacecraft ID -1024)
  appeared in the sky from one 70 m antenna at each complex (DSS-14, DSS-43,
  DSS-63). Ingested by `pipelines.ingest.jpl_dsn_geometry`.
- **"In view" is geometry, not a schedule.** It means Orion was at least
  {ELEVATION_CUTOFF_DEG:.0f}° above the horizon. Whether an antenna was actually
  pointed at Orion depended on DSN scheduling and other missions, which this data
  doesn't include.
- **Only the DSN is shown.** Close to Earth (just after launch, just before
  re-entry) spacecraft can also be reached through other ground and relay
  networks, so gaps at the very start and end may overstate real loss of contact.
- Each complex has several antennas; one is used as the reference for its site.
"""
    )

with st.expander("Data check: does this agree with Orion's trajectory?"):
    st.markdown(
        "Every antenna sits on Earth's surface, so its distance to Orion can differ "
        "from Orion's distance to **Earth's centre** (from the trajectory table, "
        f"`orion_ephemeris`) by at most one Earth radius, about {R_EARTH_KM:,.0f} km. "
        "Lines outside the dotted bounds indicate a data problem."
    )
    orion = load_orion_ephemeris(engine, date_from, date_to)
    if orion.empty:
        st.info(
            "No `orion_ephemeris` rows for this window - run "
            "`uv run --package pipelines python -m pipelines.ingest.jpl_orion` to compare."
        )
    else:
        joined = df.merge(
            orion[["epoch", "range_km"]].rename(columns={"range_km": "geocentric_range_km"}),
            on="epoch",
        )
        joined["range_offset_km"] = joined["range_km"] - joined["geocentric_range_km"]
        fig_offset = px.line(
            joined,
            x="epoch",
            y="range_offset_km",
            color="label",
            color_discrete_map=SITE_COLORS,
            category_orders={"label": list(SITE_COLORS)},
            labels={
                "epoch": "Time (UTC)",
                "range_offset_km": "Site distance − centre distance (km)",
                "label": "Site",
            },
        )
        for bound in (R_EARTH_KM, -R_EARTH_KM):
            fig_offset.add_hline(y=bound, line_dash="dot", line_color="#898781")
        fig_offset.update_layout(legend={"orientation": "h", "y": 1.08, "x": 0, "title": None})
        st.plotly_chart(fig_offset, width="stretch")

        out_of_bounds = joined["range_offset_km"].abs() > R_EARTH_KM * 1.01
        if out_of_bounds.any():
            st.error(
                f"{int(out_of_bounds.sum())} rows differ from the centre distance by more "
                "than one Earth radius, which no surface site can do. Check that both "
                "tables use the same time scale: these epochs are UTC, and Horizons "
                "vector tables are stamped in TDB (~69 s ahead in 2026)."
            )
        else:
            st.success(f"All {len(joined)} matched rows are within one Earth radius.")

with st.expander("Raw data"):
    st.dataframe(
        df.drop(columns=["label"]),
        width="stretch",
        hide_index=True,
    )
