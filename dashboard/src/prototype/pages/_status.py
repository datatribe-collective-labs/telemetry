"""Plain-language wording and colors for the models' state codes."""

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


def status(table: dict[str, tuple[str, str]], state: str) -> tuple[str, str]:
    """(label, Streamlit color name) for a state code; unknown codes show as-is in grey."""
    return table.get(state, (state.replace("_", " ").capitalize(), "gray"))


def is_ok(state: str) -> bool:
    return state == "NOMINAL"
