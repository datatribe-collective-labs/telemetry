"""Radiation journey helpers: dose by source and chapter, and the page's two charts."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dashboard.src.prototype.views._status import MGY_PER_KRAD
from dashboard.src.prototype.views._timeline import thin

UGY_MIN_PER_RAD_S = 600_000  # 1 rad = 10 mGy = 10,000 µGy; 60 s per minute
BELT_COLOR = "#E8590C"
COSMIC_COLOR = "#3B5BDB"
RATE_COLOR = "#C2410C"
NOW_COLOR = "#26324A"


@dataclass(frozen=True)
class DoseTotals:
    total_mgy: float
    belts_mgy: float
    cosmic_mgy: float
    peak_ugy_min: float


@dataclass(frozen=True)
class ChapterDoses:
    leaving_mgy: float
    quiet_mgy: float
    home_mgy: float
    quiet_start: pd.Timestamp
    home_start: pd.Timestamp


def usable_rows(radiation: pd.DataFrame) -> pd.DataFrame:
    """Rows with the dose-by-source fields; ones written before those fields existed have none."""
    if radiation.empty:
        return radiation
    needed = ["cumulative_dose_krad", "cumulative_belt_dose_krad", "total_dose_rate_rad_s", "radiation_zone"]
    return radiation.dropna(subset=needed).reset_index(drop=True)


def dose_totals(radiation: pd.DataFrame) -> DoseTotals:
    """Totals at the last row, and the highest dose rate."""
    last = radiation.iloc[-1]
    total = float(last["cumulative_dose_krad"]) * MGY_PER_KRAD
    belts = float(last["cumulative_belt_dose_krad"]) * MGY_PER_KRAD
    peak = float(radiation["total_dose_rate_rad_s"].max()) * UGY_MIN_PER_RAD_S
    return DoseTotals(total, belts, total - belts, peak)


def chapter_doses(radiation: pd.DataFrame) -> ChapterDoses | None:
    """Dose in the three flight stages; None until the stored mission reaches the return belts.

    Leaving ends at the first deep-space row after the inner belt, and coming home starts
    after the last deep-space row, so the three always add up to the total.
    """
    if radiation.empty:
        return None
    zones = radiation["radiation_zone"].to_numpy()
    inner = np.flatnonzero(zones == "INNER_BELT")
    deep = np.flatnonzero(zones == "DEEP_SPACE")
    if not len(inner):
        return None
    deep = deep[deep > inner[0]]
    if not len(deep) or deep[-1] == len(zones) - 1:
        return None
    first, last = int(deep[0]), int(deep[-1])
    dose = radiation["cumulative_dose_krad"].to_numpy() * MGY_PER_KRAD
    times = radiation["timestamp_utc"]
    return ChapterDoses(float(dose[first - 1]), float(dose[last] - dose[first - 1]), float(dose[-1] - dose[last]),
                        times.iloc[first], times.iloc[last + 1])


def _mark_now(fig: go.Figure, now, label: str) -> None:
    """A short mark above the plot, so it never hides a peak."""
    if now is None:
        return
    fig.add_shape(type="line", x0=now, x1=now, y0=0.94, y1=1, yref="paper", line={"color": NOW_COLOR, "width": 3})
    fig.add_annotation(x=now, y=1, yref="paper", yanchor="bottom", text=f"<b>{label}</b>", showarrow=False,
                       font={"color": NOW_COLOR, "size": 12})


def dose_rate_chart(radiation: pd.DataFrame, now=None, now_label: str = "You are here") -> go.Figure:
    """Total dose rate in µGy/min on a log axis. Thinned without losing peaks or zone changes."""
    rows = radiation.assign(rate_ugy_min=radiation["total_dose_rate_rad_s"] * UGY_MIN_PER_RAD_S)
    line = thin(rows[["timestamp_utc", "rate_ugy_min", "radiation_zone"]], ["rate_ugy_min"], flags=("radiation_zone",))
    fig = go.Figure(go.Scatter(
        x=line["timestamp_utc"], y=line["rate_ugy_min"], mode="lines", name="Dose rate", connectgaps=False,
        line={"color": RATE_COLOR, "width": 2},
        hovertemplate="%{x|%b %d %H:%M} UTC<br>%{y:.2f} µGy/min<extra></extra>",
    ))
    _mark_now(fig, now, now_label)
    fig.update_layout(height=320, margin={"l": 0, "r": 0, "t": 24, "b": 0}, showlegend=False, yaxis_title="µGy/min")
    # Label powers of ten only: Plotly's default minor labels show 0.2 and 0.5 as "2" and "5".
    ticks = [0.01, 0.1, 1, 10, 100, 1000]
    fig.update_yaxes(type="log", tickvals=ticks, ticktext=[f"{t:g}" for t in ticks])
    return fig


def cumulative_chart(radiation: pd.DataFrame, now=None, now_label: str = "You are here") -> go.Figure:
    """Cumulative dose in mGy, stacked by source."""
    total = radiation["cumulative_dose_krad"] * MGY_PER_KRAD
    belts = radiation["cumulative_belt_dose_krad"] * MGY_PER_KRAD
    rows = radiation[["timestamp_utc", "radiation_zone"]].assign(belts_mgy=belts, cosmic_mgy=total - belts)
    # A stacked area treats blank rows as zero, so drop the line-break rows here.
    area = thin(rows, ["belts_mgy", "cosmic_mgy"], flags=("radiation_zone",)).dropna(subset=["timestamp_utc"])
    fig = go.Figure()
    for column, name, color in (("belts_mgy", "Radiation belts", BELT_COLOR), ("cosmic_mgy", "Cosmic rays", COSMIC_COLOR)):
        fig.add_trace(go.Scatter(
            x=area["timestamp_utc"], y=area[column], mode="lines", name=name, stackgroup="dose",
            line={"color": color, "width": 1},
            hovertemplate=f"{name}: %{{y:.2f}} mGy<extra></extra>",
        ))
    _mark_now(fig, now, now_label)
    fig.update_layout(height=320, margin={"l": 0, "r": 0, "t": 24, "b": 0}, hovermode="x unified",
                      legend={"orientation": "h", "y": 1.12, "x": 0}, yaxis_title="mGy", yaxis_rangemode="tozero")
    return fig
