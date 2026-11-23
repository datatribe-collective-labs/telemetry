"""Radiation journey page: what did the flight expose Orion's cabin to, and why?

Always the whole stored mission, with a marker at the live or replay moment. The dose is
simulated at one cabin sensor and is not the crew's actual dose.
"""

import pandas as pd
import streamlit as st

from dashboard.src.prototype.data.backend_api import BackendAPIError
from dashboard.src.prototype.views import _data
from dashboard.src.prototype.views._blackout import BLACKOUT_END, BLACKOUT_START
from dashboard.src.prototype.views._controls import (
    LIFTOFF,
    MISSION_END,
    MISSION_START,
    time_window,
)
from dashboard.src.prototype.views._explain import data_badge, explain
from dashboard.src.prototype.views._link import duration_text
from dashboard.src.prototype.views._live import REFRESH_INTERVAL, plot
from dashboard.src.prototype.views._radiation import (
    chapter_doses,
    cumulative_chart,
    dose_rate_chart,
    dose_totals,
    usable_rows,
)
from dashboard.src.prototype.views._status import (
    STORM_PFU,
    format_dose,
    radiation_zone,
    storm_summary,
)
from dashboard.src.prototype.views._trajectory import up_to

st.title("What did the journey expose Orion's cabin to?")
st.markdown(f"{data_badge('synthetic')} A simulated absorbed dose in water at one cabin sensor, calibrated to "
            "Artemis I. **This is not the crew's actual dose.**")

date_from, date_to, live = time_window()


def _here(radiation: pd.DataFrame, now) -> None:
    rows = up_to(radiation, now)
    if rows.empty:
        st.caption("The simulated dose starts on Apr 2 at 02:00 UTC, when NASA's trajectory data begins.")
        return
    row = rows.iloc[-1]
    label, _, sentence = radiation_zone(row["radiation_zone"])
    st.markdown(f"**At {row['timestamp_utc']:%b %d, %H:%M} UTC:** {label}, {format_dose(row['cumulative_dose_krad'])} "
                f"so far. {sentence}")


def _chapters(chapters, goes) -> None:
    st.subheader("The journey in five chapters")
    explain("radiation.chapters")
    st.markdown(f"**1 · Leaving Earth's shield: {chapters.leaving_mgy:.2f} mGy.** Orion crossed the radiation belts "
                "around its last close pass of Earth, going through the inner belt on the way in and on the way "
                "out. More than half of the flight's dose came in this first day.")
    days = (chapters.home_start - chapters.quiet_start) / pd.Timedelta("1D")
    st.markdown(f"**2 · The long quiet: {chapters.quiet_mgy:.2f} mGy.** For about {days:.1f} days beyond the belts, "
                "cosmic rays were the only source. The rate is tiny, but it never stops.")
    blackout = duration_text(BLACKOUT_END - BLACKOUT_START)
    st.markdown(f"**3 · Behind the Moon.** The Moon cut the radio for {blackout}, but from about 6,544 km up it "
                "covered only about 1.1% of the sky, so it barely shielded Orion from cosmic rays. Artemis I "
                "passed about 130 km from the Moon, where cosmic-ray doses fell by a third.")

    st.markdown("**4 · The storm that didn't come.**")
    explain("radiation.storm")
    storm = storm_summary(goes, LIFTOFF) if goes is not None else None
    if storm is None:
        st.caption("Real solar particle data is not available.")
    elif storm.storm:
        st.markdown(f"Solar particles reached **{storm.peak_pfu:.2f} pfu**, above the {STORM_PFU} pfu storm level.")
    else:
        st.markdown(f"Solar particles peaked at **{storm.peak_pfu:.2f} pfu** on {storm.peak_time:%b %d}, below the "
                    f"**{STORM_PFU} pfu** storm level, so no solar radiation storm reached Orion.")
    st.info("**What if? Not an Artemis II event.** The Artemis I paper simulated the large solar particle event of "
            "October 1989 for that spacecraft. The peak dose rate was **414 µGy/min** at the crew cabin sensor and "
            "**95 µGy/min** in the storm shelter.")

    st.markdown(f"{data_badge('synthetic')} **5 · Coming home: {chapters.home_mgy:.2f} mGy.** A second belt crossing "
                "on the way back. NASA's trajectory data ends before splashdown, so the last part of the descent "
                "isn't counted.")


@st.fragment(run_every=REFRESH_INTERVAL if live else None)
def render(date_to, live):
    try:
        stored = _data.stored_mission("radiation", MISSION_START, None)
        current = _data.synthetic_radiation(MISSION_START, None) if live else stored
    except BackendAPIError as e:
        st.error(str(e))
        return
    try:
        goes = _data.goes_protons(MISSION_START, MISSION_END)
    except BackendAPIError:
        goes = None

    whole = usable_rows(stored if len(stored) >= len(current) else current)
    if whole.empty:
        st.info("No simulated radiation yet. Start the physics model (see RUN_SERVICES.md).")
        return
    latest = usable_rows(current)
    now = latest["timestamp_utc"].iloc[-1] if live and not latest.empty else (None if live else date_to)
    now_label = "You are here" if live else "End of selected time"
    if now is not None:
        now = min(pd.Timestamp(now), whole["timestamp_utc"].iloc[-1])

    totals = dose_totals(whole)
    chapters = chapter_doses(whole)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Over the trajectory data" if chapters else "Stored so far", f"{totals.total_mgy:.2f} mGy")
    c2.metric("From radiation belts", f"{totals.belts_mgy:.2f} mGy")
    c3.metric("From cosmic rays", f"{totals.cosmic_mgy:.2f} mGy")
    c4.metric("Peak dose rate (calibrated)", f"{totals.peak_ugy_min:.0f} µGy/min")
    if not chapters:
        st.info("The full journey appears once the simulator has stored a whole mission.")
    _here(whole, now)

    st.subheader("Dose rate: short spikes, then a long quiet")
    explain("radiation.rate")
    plot(dose_rate_chart(whole, now, now_label))

    st.subheader("Cumulative dose by source")
    explain("radiation.total")
    plot(cumulative_chart(whole, now, now_label))

    if chapters:
        _chapters(chapters, goes)


render(date_to, live)
