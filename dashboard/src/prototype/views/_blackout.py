"""The lunar flyby blackout on the real-data Space environment page.

`dsn_site_geometry.visible` only checks elevation, so it says a site can reach Orion
while the Moon is in the way. This page shows real data only, so it uses NASA's planned
window (6:44 to 7:25 p.m. EDT on April 6), not the simulator's Moon-blocking model.
"""

from dataclasses import dataclass

import pandas as pd

from dashboard.src.prototype.views._timeline import true_intervals

BLACKOUT_START = pd.Timestamp("2026-04-06 22:44", tz="UTC")
BLACKOUT_END = pd.Timestamp("2026-04-06 23:25", tz="UTC")
DSN_STEP = pd.Timedelta("1h")  # dsn_site_geometry cadence

Span = tuple[pd.Timestamp, pd.Timestamp]


@dataclass(frozen=True)
class ContactSummary:
    coverage: float  # share of the time at least one site could reach Orion
    longest_gap: pd.Timedelta
    gaps: list[Span]  # every stretch with no contact, including the blackout


def in_blackout(t) -> bool:
    return BLACKOUT_START <= pd.Timestamp(t) < BLACKOUT_END


def cut_blackout(spans: list[Span]) -> list[Span]:
    """The same time spans with the blackout removed."""
    out: list[Span] = []
    for start, end in spans:
        if end <= BLACKOUT_START or start >= BLACKOUT_END:
            out.append((start, end))
            continue
        if start < BLACKOUT_START:
            out.append((start, BLACKOUT_START))
        if end > BLACKOUT_END:
            out.append((BLACKOUT_END, end))
    return out


def _merge(spans: list[Span]) -> list[Span]:
    merged: list[Span] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def contact_summary(dsn: pd.DataFrame) -> ContactSummary:
    """Coverage and gaps from the hourly geometry, counting the blackout as no contact."""
    if dsn.empty:
        return ContactSummary(0.0, pd.Timedelta(0), [])
    any_visible = dsn.assign(visible=dsn["visible"].fillna(False).astype(bool)).groupby("epoch")["visible"].any()
    first, last = any_visible.index.min(), any_visible.index.max()
    if first == last:
        reachable = bool(any_visible.iloc[0]) and not in_blackout(first)
        return ContactSummary(float(reachable), pd.Timedelta(0), [])
    spans = true_intervals(any_visible.index.to_series(), ~any_visible, max_gap=DSN_STEP)
    start, end = max(first, BLACKOUT_START), min(last, BLACKOUT_END)
    if start < end:
        spans.append((start, end))
    gaps = _merge(spans)
    lost = sum((e - s for s, e in gaps), pd.Timedelta(0))
    longest = max((e - s for s, e in gaps), default=pd.Timedelta(0))
    return ContactSummary(1 - lost / (last - first), longest, gaps)


def sites_in_view(dsn: pd.DataFrame) -> list[tuple[str, float]]:
    """(site, elevation) for each complex with Orion above its horizon during the blackout."""
    middle = BLACKOUT_START + (BLACKOUT_END - BLACKOUT_START) / 2
    before = dsn[dsn["epoch"] <= middle] if not dsn.empty else dsn
    if before.empty:
        return []
    at = before[before["epoch"] == before["epoch"].max()]
    at = at[at["visible"].fillna(False).astype(bool)]
    return [(row["complex"], float(row["elevation_deg"])) for _, row in at.iterrows()]
