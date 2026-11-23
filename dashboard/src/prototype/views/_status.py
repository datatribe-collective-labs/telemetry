"""Plain-language wording and colors for the models' state codes."""

from dataclasses import dataclass

import pandas as pd

THERMAL_STATUS: dict[str, tuple[str, str]] = {
    "NOMINAL": ("Temperature OK", "green"),
    "COLD_SURVIVAL": ("Too cold, heater on", "blue"),
    "HOT_LIMIT": ("Too hot", "red"),
}

POWER_STATUS: dict[str, tuple[str, str]] = {
    "NOMINAL": ("Power OK", "green"),
    "BATTERY_DISCHARGE": ("Running on battery", "orange"),
    "LOW_POWER_MODE": ("Battery low", "orange"),
    "CRITICAL": ("Battery critical", "red"),
}

LINK_STATUS: dict[str, tuple[str, str]] = {
    "NOMINAL": ("Connected", "green"),
    "DEGRADED": ("Weak signal", "orange"),
}

# Why a link is down. Grey and blue: expected geometry. Red: something is wrong.
LINK_LOSS_STATUS: dict[str, tuple[str, str]] = {
    "OUT_OF_DSN_VIEW": ("Out of DSN view", "gray"),
    "MOON_BLOCKED": ("Behind the Moon", "blue"),
    "NO_POWER": ("Radio off: no power", "red"),
    "LINK_BUDGET": ("Signal too weak", "red"),
}

# Gaps caused by where Orion is: the end of "Earth can't reach Orion right now: ...".
EXPECTED_GAPS: dict[str, str] = {
    "OUT_OF_DSN_VIEW": "no Deep Space Network antenna can see it",
    "MOON_BLOCKED": "it is behind the Moon",
}

# (label, color, one plain sentence). Zones are places, not faults, so none is a warning color.
RADIATION_ZONES: dict[str, tuple[str, str, str]] = {
    "LOW_EARTH": ("Near Earth", "gray", "Close to Earth, below the radiation belts."),
    "INNER_BELT": ("Inner belt", "blue", "Crossing the inner radiation belt."),
    "OUTER_BELT": ("Outer belt", "blue", "Crossing the outer radiation belt."),
    "DEEP_SPACE": ("Deep space", "gray", "Beyond the belts, where cosmic rays are the main source."),
}

MGY_PER_KRAD = 10_000  # 1 krad = 10 Gy
STORM_PFU = 10  # NOAA S1, on the >=10 MeV integral proton flux


@dataclass(frozen=True)
class StormSummary:
    storm: bool
    peak_pfu: float
    peak_time: pd.Timestamp


def status(table: dict[str, tuple[str, str]], state: str) -> tuple[str, str]:
    """(label, Streamlit color name) for a state code; unknown codes show as-is in grey."""
    return table.get(state, (state.replace("_", " ").capitalize(), "gray"))


def is_ok(state: str) -> bool:
    return state == "NOMINAL"


def link_status(comm_state: str, reason: str | None) -> tuple[str, str]:
    """(label, color) for the radio link; a lost link is named by its reason."""
    if comm_state != "NO_LINK":
        return status(LINK_STATUS, comm_state)
    return LINK_LOSS_STATUS.get(reason, ("No link", "orange"))


def link_is_expected(comm_state: str, reason: str | None) -> bool:
    """True for a lost link that Orion's position explains."""
    return comm_state == "NO_LINK" and reason in EXPECTED_GAPS


def link_needs_attention(comm_state: str, reason: str | None) -> bool:
    """A weak or lost link, unless Orion's position explains it."""
    return comm_state != "NOMINAL" and not link_is_expected(comm_state, reason)


def radiation_zone(zone: str | None) -> tuple[str, str, str]:
    """(label, color, sentence); rows written before the zone existed have none."""
    return RADIATION_ZONES.get(zone, ("Not available", "gray", "No radiation zone for this moment."))


def storm_summary(goes: pd.DataFrame, start) -> StormSummary | None:
    """Did the proton flux reach NOAA's storm level from `start` on? None without data."""
    if goes.empty:
        return None
    flux = goes.dropna(subset=["p10_pfu"])
    flux = flux[flux["time"] >= pd.Timestamp(start)]
    if flux.empty:
        return None
    peak = flux.loc[flux["p10_pfu"].idxmax()]
    return StormSummary(bool(peak["p10_pfu"] >= STORM_PFU), float(peak["p10_pfu"]), peak["time"])


def format_dose(krad: float) -> str:
    """Absorbed dose in water, in mGy, or µGy below 1 mGy (the API's krad is unreadable)."""
    mgy = krad * MGY_PER_KRAD
    return f"{mgy:.2f} mGy" if mgy >= 1 else f"{mgy * 1000:.0f} µGy"
