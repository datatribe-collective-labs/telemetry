"""Trajectory page — Real (JPL Horizons) vs Synthetic (StateEngine) comparison."""

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.src.prototype.data.backend_api import (
    MAX_LIMIT,
    BackendAPIError,
    SyncBackendAPI,
    get_api,
)
from dashboard.src.prototype.pages._explain import explain
from dashboard.src.prototype.pages._live import (
    CACHE_TTL_S,
    REFRESH_INTERVAL,
    live_toggle,
    plot,
)

st.title("Trajectory — Real vs Synthetic")
st.caption("JPL Horizons ephemeris (ground truth) vs StateEngine physics model output")


# Sidebar
with st.sidebar:
    st.header("Time Range")
    # Window anchored to the Artemis II mission/replay window (synthetic + real data span Apr 1-10, 2026)
    default_end = datetime(2026, 4, 10, 23, 59, tzinfo=UTC)
    default_start = datetime(2026, 4, 1, 0, 0, tzinfo=UTC)
    
    date_range = st.date_input(
        "Date Range (UTC)",
        value=(default_start.date(), default_end.date()),
        key="traj_date_range"
    )
    
    t_start = st.time_input("Start time (UTC)", value=default_start.time(), key="trajectory_time_start")
    t_end = st.time_input("End time (UTC)", value=default_end.time(), key="trajectory_time_end")
    
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        date_from = datetime.combine(date_range[0], t_start, tzinfo=UTC)
        date_to = datetime.combine(date_range[1], t_end, tzinfo=UTC)
    else:
        date_from = default_start
        date_to = default_end
    
    limit = st.number_input("Max Points", 10, MAX_LIMIT, 500, 50, key="traj_limit")
    show_residuals = st.checkbox("Show Residuals (Real - Synthetic)", value=True)
    traj_view = st.radio(
        "Trajectory map", ["Top-down (2D)", "3D", "Hide"], key="traj_view",
        help="Top-down looks down on Earth's North Pole; 3D can be rotated with the mouse.",
    )
    
    live = live_toggle(key="traj_live")

    if st.button("Refresh", key="traj_refresh"):
        st.rerun()


api: SyncBackendAPI = get_api()


@st.cache_data(ttl=CACHE_TTL_S)
def fetch_synthetic_state(date_from, date_to, limit):
    return api.get_synthetic_state(date_from=date_from, date_to=date_to, limit=limit)


@st.cache_data(ttl=10)
def fetch_real_orion(date_from, date_to, limit):
    return api.get_orion_ephemeris(date_from=date_from, date_to=date_to, limit=limit)


REAL_COLOR = "#1F77B4"
SYN_COLOR = "#FF7F0E"
EARTH_COLOR = "#2E86DE"


def _hover_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Time, distance from Earth and speed for each row, as plotly customdata."""
    return pd.DataFrame({
        "when": df["timestamp_utc"].dt.strftime("%b %d %H:%M UTC"),
        "dist_km": np.sqrt(df["x_km"] ** 2 + df["y_km"] ** 2 + df["z_km"] ** 2),
        "speed_kms": np.sqrt(df["vx_kms"] ** 2 + df["vy_kms"] ** 2 + df["vz_kms"] ** 2),
    })


def trajectory_map(real_df: pd.DataFrame, syn_df: pd.DataFrame, three_d: bool) -> go.Figure:
    """Earth-centered map of the real and simulated paths, with labeled landmarks.

    2D is the EME2000 X-Y plane, i.e. looking down on Earth's North Pole.
    """
    trace = go.Scatter3d if three_d else go.Scatter
    hover = "<b>%s</b><br>%%{customdata[0]}<br>%%{customdata[1]:,.0f} km from Earth<br>%%{customdata[2]:.2f} km/s<extra></extra>"

    def xyz(df):
        return {"x": df["x_km"], "y": df["y_km"], **({"z": df["z_km"]} if three_d else {})}

    # Labels are arrow annotations offset in different directions (ax/ay, in pixels), so
    # "Earth" and "Orion now" stay readable while Orion is still close to Earth.
    annotations = []

    def landmark(x, y, z, name, text, symbol, color, size, ax, ay):
        point = {"x": [x], "y": [y], **({"z": [z]} if three_d else {})}
        annotations.append({"x": x, "y": y, **({"z": z} if three_d else {}), "text": text, "ax": ax, "ay": ay,
                            "showarrow": True, "arrowhead": 0, "arrowcolor": color, "font": {"size": 12},
                            "bgcolor": "rgba(255,255,255,0.8)"})
        return trace(**point, mode="markers", name=name,
                     marker={"size": size, "color": color, "symbol": symbol, "line": {"color": "white", "width": 2}},
                     hoverinfo="text", hovertext=[text.replace("<br>", " · ")])

    fig = go.Figure()
    fig.add_trace(landmark(0, 0, 0, "Earth", "<b>Earth</b>", "circle", EARTH_COLOR, 14, 45, 30))

    if not real_df.empty:
        real = real_df.dropna(subset=["x_km", "y_km", "z_km"])
        fields = _hover_fields(real)
        fig.add_trace(trace(**xyz(real), mode="lines", name="Real path (NASA/JPL)",
                            line={"color": REAL_COLOR, "width": 8 if three_d else 10}, opacity=0.45,
                            customdata=fields, hovertemplate=hover % "Real (NASA/JPL)"))
        far = real.loc[fields["dist_km"].idxmax()]
        fig.add_trace(landmark(far["x_km"], far["y_km"], far["z_km"], "Farthest from Earth",
                               f"<b>Farthest from Earth</b> (lunar flyby)<br>{fields.loc[far.name, 'when']} · "
                               f"{fields.loc[far.name, 'dist_km']:,.0f} km",
                               "diamond", REAL_COLOR, 11, 110, -10))

    if not syn_df.empty:
        fields = _hover_fields(syn_df)
        fig.add_trace(trace(**xyz(syn_df), mode="lines", name="Simulated path (digital twin)",
                            line={"color": SYN_COLOR, "width": 3},
                            customdata=fields, hovertemplate=hover % "Simulated (digital twin)"))
        now = syn_df.loc[syn_df.index[-1]]
        fig.add_trace(landmark(now["x_km"], now["y_km"], now["z_km"], "Orion now (simulated)",
                               f"<b>Orion now</b> (simulated)<br>{fields.loc[now.name, 'when']} · "
                               f"{fields.loc[now.name, 'dist_km']:,.0f} km from Earth",
                               "circle", SYN_COLOR, 16, -110, -45))

    layout = {"height": 600, "margin": {"l": 60, "r": 10, "t": 10, "b": 40},
              "legend": {"orientation": "h", "y": -0.12}}
    if three_d:
        layout["scene"] = {"xaxis_title": "km", "yaxis_title": "km", "zaxis_title": "km (north)",
                           "aspectmode": "data", "annotations": annotations,
                           "camera": {"eye": {"x": 1.6, "y": -1.6, "z": 1.1}}}
    else:
        layout |= {"xaxis": {"title": "km", "zeroline": False},
                   "yaxis": {"title": "km", "zeroline": False, "scaleanchor": "x", "scaleratio": 1},
                   "annotations": [{**a, "xref": "x", "yref": "y"} for a in annotations]}
    fig.update_layout(**layout)
    return fig


@st.fragment(run_every=REFRESH_INTERVAL if live else None)
def render_trajectory(date_from, date_to, limit):
    # Fetch data
    try:
        syn_resp = fetch_synthetic_state(date_from, date_to, limit)
        syn_items = syn_resp.items if syn_resp else []
        # Real Horizons track for the whole sidebar window (drawn on the charts).
        real_resp = fetch_real_orion(date_from, date_to, limit)
        # Synthetic rows are the newest `limit` ticks, which the window fetch above can miss
        # once the real table outgrows `limit`; fetch real rows over the synthetic span too
        # so the nearest-timestamp merge below has rows to pair up.
        span_items = []
        if syn_items:
            syn_times = [s.timestamp_utc for s in syn_items]
            span_resp = fetch_real_orion(min(syn_times), max(syn_times), limit)
            span_items = span_resp.items if span_resp else []
    except BackendAPIError as e:
        st.error(str(e))
        return

    real_items = real_resp.items if real_resp else []
    if real_resp and real_resp.total > len(real_items):
        st.caption(
            f"Showing the first {len(real_items)} of {real_resp.total} JPL Horizons rows in the "
            "selected window; raise Max Points to see more."
        )

    if not syn_items and not real_items:
        st.warning("No data available for selected range.")
        return


    # Convert to DataFrames
    syn_df = pd.DataFrame([s.model_dump() for s in syn_items]) if syn_items else pd.DataFrame()
    real_df = pd.DataFrame([r.model_dump() for r in real_items]) if real_items else pd.DataFrame()
    span_df = pd.DataFrame([r.model_dump() for r in span_items]) if span_items else pd.DataFrame()

    # Real (JPL Horizons/orion_ephemeris) rows are keyed by `epoch`; synthetic rows by
    # `timestamp_utc`. Normalize real onto the shared timestamp column used below.
    if not real_df.empty and "epoch" in real_df.columns and "timestamp_utc" not in real_df.columns:
        real_df = real_df.rename(columns={"epoch": "timestamp_utc"})
    if not span_df.empty and "epoch" in span_df.columns and "timestamp_utc" not in span_df.columns:
        span_df = span_df.rename(columns={"epoch": "timestamp_utc"})

    for df in [syn_df, real_df, span_df]:
        if not df.empty and "timestamp_utc" in df.columns:
            df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
            df.sort_values("timestamp_utc", inplace=True)

    # The comparison pairs synthetic with real over the synthetic span when they overlap;
    # otherwise it falls back to the window track (and explains the missing overlap below).
    cmp_real_df = span_df if not span_df.empty else real_df


    # =========================================================================
    # TRAJECTORY MAP
    # =========================================================================
    if traj_view != "Hide" and (not syn_df.empty or not real_df.empty):
        st.subheader("Where is Orion?")
        st.caption(
            "Earth-centered map. **Blue band:** where Orion actually flew (NASA/JPL). "
            "**Orange line:** where the digital twin simulates it; the closer it follows the "
            "blue band, the better the simulation. Hover any point for time, distance and speed."
        )
        explain("trajectory.3d")
        plot(trajectory_map(real_df, syn_df, three_d=traj_view == "3D"))


    # =========================================================================
    # TIME SERIES COMPARISON
    # =========================================================================
    st.markdown("---")
    st.subheader("Position & Velocity Comparison")
    explain("trajectory.compare")

    if not syn_df.empty and not real_df.empty:
        # Merge on nearest timestamp for residuals
        merged = pd.merge_asof(
            cmp_real_df.sort_values("timestamp_utc"),
            syn_df.sort_values("timestamp_utc"),
            on="timestamp_utc",
            direction="nearest",
            tolerance=pd.Timedelta("30s"),
            suffixes=("_real", "_syn")
        )
    
        if not merged.empty:
            # Compute residuals
            for coord in ["x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms"]:
                if f"{coord}_real" in merged.columns and f"{coord}_syn" in merged.columns:
                    merged[f"{coord}_residual"] = merged[f"{coord}_real"] - merged[f"{coord}_syn"]
        
            if "range_km" in merged.columns and "earth_distance_km" in merged.columns:
                merged["range_residual_km"] = merged["range_km"] - merged["earth_distance_km"]
        
            if "speed_kms" in merged.columns:
                merged["speed_syn"] = np.sqrt(merged["vx_kms_syn"]**2 + merged["vy_kms_syn"]**2 + merged["vz_kms_syn"]**2)
                merged["speed_residual"] = merged["speed_kms"] - merged["speed_syn"]
    
        # Position plots
        c1, c2 = st.columns(2)
    
        with c1:
            st.markdown("**Position (km)**")
            fig = go.Figure()
            for coord, color in [("x_km", "#00D2FF"), ("y_km", "#FF6B6B"), ("z_km", "#4ECDC4")]:
                if f"{coord}_real" in merged.columns:
                    fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged[f"{coord}_real"], name=f"Real {coord.upper()}", line={"color": color, "width": 2}))
                if f"{coord}_syn" in merged.columns:
                    fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged[f"{coord}_syn"], name=f"Syn {coord.upper()}", line={"color": color, "width": 2, "dash": "dash"}))
            fig.update_layout(height=350, margin={"l": 0, "r": 0, "t": 30, "b": 0}, legend={"orientation": "h", "y": -0.2})
            plot(fig)
        
            if show_residuals:
                st.markdown("**Position Residuals (Real - Synthetic)**")
                fig = go.Figure()
                for coord, color in [("x_km", "#00D2FF"), ("y_km", "#FF6B6B"), ("z_km", "#4ECDC4")]:
                    if f"{coord}_residual" in merged.columns:
                        fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged[f"{coord}_residual"], name=f"Δ{coord.upper()}", line={"color": color, "width": 2}))
                fig.update_layout(height=200, margin={"l": 0, "r": 0, "t": 30, "b": 0}, yaxis_title="Residual (km)")
                plot(fig)
    
        with c2:
            st.markdown("**Velocity (km/s)**")
            fig = go.Figure()
            for coord, color in [("vx_kms", "#00D2FF"), ("vy_kms", "#FF6B6B"), ("vz_kms", "#4ECDC4")]:
                if f"{coord}_real" in merged.columns:
                    fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged[f"{coord}_real"], name=f"Real {coord.upper()}", line={"color": color, "width": 2}))
                if f"{coord}_syn" in merged.columns:
                    fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged[f"{coord}_syn"], name=f"Syn {coord.upper()}", line={"color": color, "width": 2, "dash": "dash"}))
            fig.update_layout(height=350, margin={"l": 0, "r": 0, "t": 30, "b": 0}, legend={"orientation": "h", "y": -0.2})
            plot(fig)
        
            if show_residuals:
                st.markdown("**Velocity Residuals (Real - Synthetic)**")
                fig = go.Figure()
                for coord, color in [("vx_kms", "#00D2FF"), ("vy_kms", "#FF6B6B"), ("vz_kms", "#4ECDC4")]:
                    if f"{coord}_residual" in merged.columns:
                        fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged[f"{coord}_residual"], name=f"Δ{coord.upper()}", line={"color": color, "width": 2}))
                fig.update_layout(height=200, margin={"l": 0, "r": 0, "t": 30, "b": 0}, yaxis_title="Residual (km/s)")
                plot(fig)
    
        # Range & Speed
        st.markdown("**Range & Speed**")
        c3, c4 = st.columns(2)
    
        with c3:
            fig = go.Figure()
            if "range_km" in merged.columns:
                fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged["range_km"], name="Real Range", line={"color": "#00D2FF", "width": 2}))
            if "earth_distance_km" in merged.columns:
                fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged["earth_distance_km"], name="Syn Earth Dist", line={"color": "#FF6B6B", "width": 2, "dash": "dash"}))
            fig.update_layout(title="Range from Earth (km)", height=300, margin={"l": 0, "r": 0, "t": 30, "b": 0})
            plot(fig)
        
            if show_residuals and "range_residual_km" in merged.columns:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged["range_residual_km"], name="Range Residual", line={"color": "#EF553B", "width": 2}))
                fig.update_layout(title="Range Residual (km)", height=150, margin={"l": 0, "r": 0, "t": 30, "b": 0})
                plot(fig)
    
        with c4:
            fig = go.Figure()
            if "speed_kms" in merged.columns:
                fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged["speed_kms"], name="Real Speed", line={"color": "#00D2FF", "width": 2}))
            if "speed_syn" in merged.columns:
                fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged["speed_syn"], name="Syn Speed", line={"color": "#FF6B6B", "width": 2, "dash": "dash"}))
            fig.update_layout(title="Speed Magnitude (km/s)", height=300, margin={"l": 0, "r": 0, "t": 30, "b": 0})
            plot(fig)
        
            if show_residuals and "speed_residual" in merged.columns:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=merged["timestamp_utc"], y=merged["speed_residual"], name="Speed Residual", line={"color": "#EF553B", "width": 2}))
                fig.update_layout(title="Speed Residual (km/s)", height=150, margin={"l": 0, "r": 0, "t": 30, "b": 0})
                plot(fig)
    
        # Residual statistics
        if show_residuals:
            st.markdown("---")
            st.subheader("Residual Statistics (Real - Synthetic)")
            explain("trajectory.residuals")

            # Residual columns are all-NaN when no timestamps line up (real JPL arc starts
            # Apr 2 ~02:00 at 4-min cadence; synthetic replays from liftoff Apr 1 22:35 at
            # 1 Hz). Show an explanation instead of NaN metrics until the overlap exists.
            residual_cols = [f"{c}_residual" for c in ["x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms"] if f"{c}_residual" in merged.columns]
            matched = merged.dropna(subset=residual_cols) if residual_cols else merged.iloc[0:0]
            if matched.empty:
                syn_span = f"{syn_df['timestamp_utc'].min():%b %d %H:%M} – {syn_df['timestamp_utc'].max():%b %d %H:%M}Z"
                real_span = f"{real_df['timestamp_utc'].min():%b %d %H:%M} – {real_df['timestamp_utc'].max():%b %d %H:%M}Z"
                st.info(
                    f"No overlapping timestamps yet — real JPL data spans **{real_span}**, "
                    f"synthetic replay currently spans **{syn_span}**. Residuals appear once the "
                    "simulation clock crosses the real-arc start (replay runs 1:1 from liftoff, "
                    "so this fills in as it reaches Apr 2 ~02:00)."
                )
            else:
                stats_cols = st.columns(6)
                for i, (coord, label) in enumerate([("x_km", "X"), ("y_km", "Y"), ("z_km", "Z"), ("vx_kms", "VX"), ("vy_kms", "VY"), ("vz_kms", "VZ")]):
                    col = f"{coord}_residual"
                    if col in merged.columns:
                        vals = merged[col].dropna()
                        with stats_cols[i]:
                            st.metric(f"Δ{label} Mean", f"{vals.mean():.3f}")
                            st.caption(f"Std: {vals.std():.3f} | Max: {vals.max():.3f}")

    elif not syn_df.empty:
        st.info("Only synthetic data available. Run JPL Horizons ingestion for real comparison.")
        # Show synthetic only
        c1, c2 = st.columns(2)
        with c1:
            fig = px.line(syn_df, x="timestamp_utc", y=["x_km", "y_km", "z_km"], title="Synthetic Position")
            plot(fig)
        with c2:
            fig = px.line(syn_df, x="timestamp_utc", y=["vx_kms", "vy_kms", "vz_kms"], title="Synthetic Velocity")
            plot(fig)

    elif not real_df.empty:
        st.info("Only real (JPL) data available. Run physics models for synthetic comparison.")
        c1, c2 = st.columns(2)
        with c1:
            fig = px.line(real_df, x="timestamp_utc", y=["x_km", "y_km", "z_km"], title="Real Position (JPL)")
            plot(fig)
        with c2:
            fig = px.line(real_df, x="timestamp_utc", y=["vx_kms", "vy_kms", "vz_kms"], title="Real Velocity (JPL)")
            plot(fig)


    # =========================================================================
    # SOLAR GEOMETRY & ECLIPSE
    # =========================================================================
    if not syn_df.empty:
        st.markdown("---")
        st.subheader("Solar Geometry & Eclipse (Synthetic)")
        explain("trajectory.solar")
    
        c1, c2, c3 = st.columns(3)
        with c1:
            if "solar_flux_w_m2" in syn_df.columns:
                fig = px.line(syn_df, x="timestamp_utc", y="solar_flux_w_m2", title="Solar Flux (W/m²)")
                plot(fig)
        with c2:
            if "solar_incidence_angle_deg" in syn_df.columns:
                fig = px.line(syn_df, x="timestamp_utc", y="solar_incidence_angle_deg", title="Solar Incidence Angle (°)")
                plot(fig)
        with c3:
            if "eclipse_state" in syn_df.columns:
                eclipse_map = {"SUNLIT": 0, "PENUMBRA": 0.5, "UMBRA": 1}
                syn_df["eclipse_numeric"] = syn_df["eclipse_state"].map(eclipse_map)
                fig = px.line(syn_df, x="timestamp_utc", y="eclipse_numeric", title="Eclipse State")
                fig.update_yaxes(tickvals=[0, 0.5, 1], ticktext=["SUNLIT", "PENUMBRA", "UMBRA"])
                plot(fig)


render_trajectory(date_from, None if live else date_to, limit)
