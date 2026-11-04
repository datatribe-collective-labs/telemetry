"""Trajectory helpers: the Earth-centred Orion map with the Moon, the live/replay
readout (Mission page) and the real-vs-simulated position comparison (Model accuracy page)."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.src.prototype.pages._controls import mission_clock, mission_day
from dashboard.src.prototype.pages._timeline import break_at_jumps

REAL_COLOR = "#1F77B4"  # same blue/orange as the Real/Synthetic badges
SYN_COLOR = "#FF7F0E"
EARTH_COLOR = "#2E86DE"
RING_COLOR = "#B0B7C3"
MOON_COLOR = "#8D99AE"
EARTH_DIAMETER_KM = 12_742
JET_SPEED_KMH = 900
MATCH_TOLERANCE = pd.Timedelta("30s")  # real rows are hourly, simulated ticks 1 Hz
HOURLY_TOLERANCE = pd.Timedelta("90min")  # nearest hourly Horizons row (Orion, Moon)
AXES = ["x_km", "y_km", "z_km"]


def hover_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Time, distance from Earth and speed for each row, as plotly customdata."""
    return pd.DataFrame({
        "when": df["timestamp_utc"].dt.strftime("%b %d %H:%M UTC"),
        "dist_km": np.sqrt(df["x_km"] ** 2 + df["y_km"] ** 2 + df["z_km"] ** 2),
        "speed_kms": np.sqrt(df["vx_kms"] ** 2 + df["vy_kms"] ** 2 + df["vz_kms"] ** 2),
    })


def at_time(df: pd.DataFrame, t, tolerance: pd.Timedelta = HOURLY_TOLERANCE) -> pd.Series | None:
    """The row nearest to time `t` (within `tolerance`), or None."""
    if df.empty or t is None:
        return None
    gaps = (df["timestamp_utc"] - pd.Timestamp(t)).abs()
    i = gaps.idxmin()
    return df.loc[i] if gaps[i] <= tolerance else None


def up_to(df: pd.DataFrame, t) -> pd.DataFrame:
    """Rows at or before time `t` (all rows when t is None)."""
    return df if df.empty or t is None else df[df["timestamp_utc"] <= pd.Timestamp(t)]


def orion_readout(now: pd.Series, moon: pd.Series | None = None) -> None:
    """Big numbers about Orion at one moment (the newest simulated tick when live, the
    chosen replay time otherwise); in live mode they visibly change on every refresh,
    unlike the map, where a few km per update is too small to see."""
    pos = np.array([now["x_km"], now["y_km"], now["z_km"]])
    vel = np.array([now["vx_kms"], now["vy_kms"], now["vz_kms"]])
    dist = float(np.linalg.norm(pos))
    speed_kmh = float(np.linalg.norm(vel)) * 3600
    heading_away = float(pos @ vel) > 0
    tick = now["timestamp_utc"]

    # Previous tick, for "since last update"; reset if the replay restarts.
    last = st.session_state.get("mission_last")
    if last is None or tick < last[0]:
        delta = None
    elif tick == last[0]:
        delta = last[2]
    else:
        delta = dist - last[1]
    st.session_state["mission_last"] = (tick, dist, delta)

    if delta is None or abs(delta) < 0.5:
        delta_text = None
    else:
        delta_text = f"{delta:+,.0f} km since last update"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Distance from Earth", f"{dist:,.0f} km", delta=delta_text, delta_color="off")
        st.caption(f"About **{dist / EARTH_DIAMETER_KM:,.0f} Earths** lined up in a row")
    with c2:
        st.metric("Speed", f"{speed_kmh:,.0f} km/h")
        st.caption(f"About **{speed_kmh / JET_SPEED_KMH:,.1f}×** a passenger jet")
    with c3:
        st.metric("Direction", "Heading out" if heading_away else "Coming home")
        if moon is None:
            st.caption("Moving away from Earth or back toward it")
        else:
            moon_km = float(np.linalg.norm(pos - np.array([moon["x_km"], moon["y_km"], moon["z_km"]])))
            st.caption(f"Moving away from Earth or back toward it · **{moon_km:,.0f} km** from the Moon")
    with c4:
        # Ticks visibly on every update, even in Earth orbit where the distance barely changes.
        st.metric("Time since liftoff", mission_clock(tick))
        st.caption(f"Day **{mission_day(tick)}** of the mission · {tick:%b %d, %H:%M:%S} UTC")


def _ring_step(max_km: float) -> int:
    """Ring spacing that gives at most 5 distance rings."""
    for step in (10_000, 25_000, 50_000, 100_000):
        if max_km / step <= 5:
            return step
    return 200_000


def trajectory_map(real_df: pd.DataFrame, syn_df: pd.DataFrame, three_d: bool,
                   moon_df: pd.DataFrame | None = None, replay_at=None) -> go.Figure:
    """Earth-centred map: distance rings instead of X/Y/Z axes, the real and simulated
    paths, the Moon's path, and labelled Earth / Moon / Orion / farthest-point landmarks.

    With `replay_at` (replay mode), the path flown by then is solid and the rest of the
    real path faint, Orion and the Moon sit where they were at that time, and the
    simulated path stops there. Otherwise Orion is at the newest simulated tick.

    2D is the EME2000 X-Y plane, i.e. looking down on Earth's North Pole.
    """
    moon_df = pd.DataFrame() if moon_df is None else moon_df
    trace = go.Scatter3d if three_d else go.Scatter
    hover = "<b>%s</b><br>%%{customdata[0]}<br>%%{customdata[1]:,.0f} km from Earth<br>%%{customdata[2]:.2f} km/s<extra></extra>"

    def xyz(df):
        return {"x": df["x_km"], "y": df["y_km"], **({"z": df["z_km"]} if three_d else {})}

    # Labels are arrow annotations offset in different directions (ax/ay, in pixels),
    # so "Earth" and "Orion" stay readable while Orion is still close to Earth.
    annotations = []

    def landmark(x, y, z, name, text, symbol, color, size, ax, ay):
        point = {"x": [x], "y": [y], **({"z": [z]} if three_d else {})}
        annotations.append({"x": x, "y": y, **({"z": z} if three_d else {}), "text": text, "ax": ax, "ay": ay,
                            "showarrow": True, "arrowhead": 0, "arrowcolor": color, "font": {"size": 13},
                            "bgcolor": "rgba(255,255,255,0.85)"})
        return trace(**point, mode="markers", name=name, showlegend=False,
                     marker={"size": size, "color": color, "symbol": symbol, "line": {"color": "white", "width": 2}},
                     hoverinfo="text", hovertext=[text.replace("<br>", " · ")])

    fig = go.Figure()

    # Distance rings around Earth (X-Y plane), labelled at the upper right in 2D and on
    # the camera-facing side in 3D (where the labels spread apart instead of stacking).
    dists = [hover_fields(df)["dist_km"].max() for df in (real_df, syn_df) if not df.empty]
    if not moon_df.empty:
        dists.append(float(np.sqrt(moon_df["x_km"] ** 2 + moon_df["y_km"] ** 2 + moon_df["z_km"] ** 2).max()))
    max_km = max([d for d in dists if pd.notna(d)] or [10_000])
    step = _ring_step(max_km)
    theta = np.linspace(0, 2 * np.pi, 181)
    for r in range(step, int(np.ceil(max_km / step)) * step + 1, step):
        ring = {"x": r * np.cos(theta), "y": r * np.sin(theta), **({"z": np.zeros_like(theta)} if three_d else {})}
        fig.add_trace(trace(**ring, mode="lines", line={"color": RING_COLOR, "width": 1, "dash": "dot"},
                            hoverinfo="skip", showlegend=False))
        angle = -np.pi / 4 if three_d else np.pi / 4
        annotations.append({"x": r * np.cos(angle), "y": r * np.sin(angle), **({"z": 0} if three_d else {}),
                            "text": f"{r:,} km", "showarrow": False, "font": {"size": 11, "color": "#6B7280"}})

    fig.add_trace(landmark(0, 0, 0, "Earth", "<b>Earth</b>", "circle", EARTH_COLOR, 16, 50, 35))

    syn_df = up_to(syn_df, replay_at)
    # Where "now" is on the map: the replay time, else the newest simulated tick.
    now_t = replay_at if replay_at is not None else (
        syn_df["timestamp_utc"].iloc[-1] if not syn_df.empty else None)

    if not moon_df.empty:
        moon = moon_df.dropna(subset=["x_km", "y_km", "z_km"])
        moon_dist = np.sqrt(moon["x_km"] ** 2 + moon["y_km"] ** 2 + moon["z_km"] ** 2)
        fig.add_trace(trace(**xyz(moon), mode="lines", name="The Moon's path",
                            line={"color": MOON_COLOR, "width": 2, "dash": "dash"},
                            customdata=pd.DataFrame({"when": moon["timestamp_utc"].dt.strftime("%b %d %H:%M UTC"),
                                                     "dist_km": moon_dist}),
                            hovertemplate="<b>Moon</b><br>%{customdata[0]}<br>"
                                          "%{customdata[1]:,.0f} km from Earth<extra></extra>"))
        here = at_time(moon, now_t) if now_t is not None else moon.iloc[-1]
        if here is not None:
            fig.add_trace(landmark(here["x_km"], here["y_km"], here["z_km"], "Moon", "<b>Moon</b>",
                                   "circle", MOON_COLOR, 22, 60, -40))

    if not real_df.empty:
        real = real_df.dropna(subset=["x_km", "y_km", "z_km"])
        fields = hover_fields(real)
        fig.add_trace(trace(**xyz(real), mode="lines", name="Path Orion really flew (NASA/JPL)",
                            line={"color": REAL_COLOR, "width": 8 if three_d else 10},
                            opacity=0.2 if replay_at is not None else 0.45,
                            customdata=fields, hovertemplate=hover % "Real (NASA/JPL)"))
        if replay_at is not None:
            flown = up_to(real, replay_at)
            if not flown.empty:
                fig.add_trace(trace(**xyz(flown), mode="lines", name="Flown by the replay time",
                                    line={"color": REAL_COLOR, "width": 8 if three_d else 10}, opacity=0.8,
                                    customdata=hover_fields(flown), hovertemplate=hover % "Real (NASA/JPL)"))
        far = real.loc[fields["dist_km"].idxmax()]
        fig.add_trace(landmark(far["x_km"], far["y_km"], far["z_km"], "Farthest point",
                               f"<b>Farthest point</b> (near the Moon)<br>{far['timestamp_utc']:%b %d} · "
                               f"{fields.loc[far.name, 'dist_km']:,.0f} km from Earth",
                               "diamond" if three_d else "star", REAL_COLOR, 14, 120, 10))

    if not syn_df.empty:
        syn_line = break_at_jumps(syn_df)
        fig.add_trace(trace(**xyz(syn_line), mode="lines", name="Our simulation (digital twin)",
                            line={"color": SYN_COLOR, "width": 3}, connectgaps=False,
                            customdata=hover_fields(syn_line), hovertemplate=hover % "Simulated (digital twin)"))
        if replay_at is None:
            now = syn_df.iloc[-1]
            dist = float(np.linalg.norm([now["x_km"], now["y_km"], now["z_km"]]))
            fig.add_trace(landmark(now["x_km"], now["y_km"], now["z_km"], "Orion now",
                                   f"<b>Orion is here</b><br>{dist:,.0f} km from Earth",
                                   "circle", SYN_COLOR, 18, -120, -50))

    if replay_at is not None:
        then = at_time(real_df, replay_at) if not real_df.empty else None
        if then is not None:
            dist = float(np.linalg.norm([then["x_km"], then["y_km"], then["z_km"]]))
            fig.add_trace(landmark(then["x_km"], then["y_km"], then["z_km"], "Orion then",
                                   f"<b>Orion on {then['timestamp_utc']:%b %d, %H:%M}</b><br>"
                                   f"{dist:,.0f} km from Earth", "circle", REAL_COLOR, 18, -120, -50))

    layout = {"height": 620, "margin": {"l": 10, "r": 10, "t": 10, "b": 10},
              "legend": {"orientation": "h", "y": -0.02}, "plot_bgcolor": "rgba(0,0,0,0)"}
    hidden = {"visible": False}
    if three_d:
        layout["scene"] = {"xaxis": hidden, "yaxis": hidden, "zaxis": hidden, "aspectmode": "data",
                           "annotations": annotations, "camera": {"eye": {"x": 1.3, "y": -1.3, "z": 1.0}}}
    else:
        layout |= {"xaxis": hidden, "yaxis": {**hidden, "scaleanchor": "x", "scaleratio": 1},
                   "annotations": [{**a, "xref": "x", "yref": "y"} for a in annotations]}
    fig.update_layout(**layout)
    return fig


def separation(real: pd.DataFrame, syn: pd.DataFrame, tolerance: pd.Timedelta = MATCH_TOLERANCE) -> pd.DataFrame:
    """Real rows paired with the nearest simulated tick within `tolerance`, plus the
    distance between the two positions (km) and the real distance from Earth (km)."""
    if real.empty or syn.empty:
        return pd.DataFrame(columns=["timestamp_utc", "separation_km", "earth_distance_km"])
    merged = pd.merge_asof(
        real[["timestamp_utc", *AXES]].sort_values("timestamp_utc"),
        syn[["timestamp_utc", *AXES]].sort_values("timestamp_utc"),
        on="timestamp_utc", direction="nearest", tolerance=tolerance, suffixes=("_real", "_syn"),
    ).dropna()
    real_xyz = merged[[f"{a}_real" for a in AXES]].to_numpy()
    syn_xyz = merged[[f"{a}_syn" for a in AXES]].to_numpy()
    return pd.DataFrame({
        "timestamp_utc": merged["timestamp_utc"],
        "separation_km": np.linalg.norm(real_xyz - syn_xyz, axis=1),
        "earth_distance_km": np.linalg.norm(real_xyz, axis=1),
    }).reset_index(drop=True)


def position_frozen(syn: pd.DataFrame) -> bool:
    """True when the two newest ticks are at different times but the same position.

    Happens before NASA's trajectory files begin (Apr 2 ~02:00 UTC) or after they end:
    the state engine then holds Orion at the nearest known point (oem.interpolate_state
    clamps to the arc edges).
    """
    if len(syn) < 2:
        return False
    last, prev = syn.iloc[-1], syn.iloc[-2]
    return last["timestamp_utc"] != prev["timestamp_utc"] and all(last[a] == prev[a] for a in AXES)
