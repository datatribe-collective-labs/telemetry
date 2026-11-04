"""Small time-series helpers shared by the pages (pure functions, unit tested)."""

import numpy as np
import pandas as pd


def true_intervals(
    times: pd.Series, flags: pd.Series, max_gap: pd.Timedelta | None = None
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Contiguous (start, end) spans where `flags` is True, for shading and Gantt bars.

    `times` must be sorted. A span ends at the first False sample after it (so hourly
    samples give hour-long bars), or at its last True sample at the end of the data.
    With `max_gap`, a span is also cut where consecutive samples are further apart
    than that (e.g. where the replay jumped), so it never bridges missing data.
    """
    spans: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    start = prev = None
    for t, flag in zip(times, flags, strict=True):
        jumped = max_gap is not None and prev is not None and t - prev > max_gap
        if start is not None and (not flag or jumped):
            spans.append((start, prev if jumped else t))
            start = None
        if flag and start is None:
            start = t
        prev = t
    if start is not None:
        spans.append((start, prev))
    return spans


MIN_JUMP = pd.Timedelta("2min")


def jump_gap(times: pd.Series) -> pd.Timedelta:
    """Spacing that counts as a jump in the data: 5x the typical tick spacing, at least
    2 min. Adapts to the producer's time scale (1 Hz ticks are 1 s of mission time at
    1x, 60 s at 60x), so speeding up the replay doesn't make every tick look like a jump."""
    typical = times.diff().median()
    return MIN_JUMP if pd.isna(typical) else max(MIN_JUMP, 5 * typical)


def break_at_jumps(df: pd.DataFrame, column: str = "timestamp_utc", gap: pd.Timedelta | None = None) -> pd.DataFrame:
    """Insert a blank row wherever time jumps by more than `gap` (default: `jump_gap`),
    so plotted lines stop there instead of drawing straight across missing data."""
    if gap is None:
        gap = jump_gap(df[column])
    jumps = np.flatnonzero(df[column].diff() > gap)
    if not len(jumps):
        return df
    # Give the blank timestamp the column's own (tz-aware) dtype: a bare NaT is
    # tz-naive and would degrade the column to object.
    blank = pd.DataFrame({
        c: pd.Series([pd.NaT], dtype=df[c].dtype) if c == column else [np.nan]
        for c in df.columns
    })
    parts, prev = [], 0
    for j in jumps:
        parts += [df.iloc[prev:j], blank]
        prev = j
    parts.append(df.iloc[prev:])
    return pd.concat(parts, ignore_index=True)
