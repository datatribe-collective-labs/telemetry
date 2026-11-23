"""Data-source badges, one-line summaries and explainers for every chart.

Each chart calls ``explain("<page>.<chart>")``, which renders, from the three
dicts below (all keyed the same; a unit test keeps them in sync with the pages):
  1. badges saying where the data comes from (SOURCES),
  2. one plain-language sentence (SUMMARIES),
  3. an "About this chart" expander with What / How to read / Why (EXPLAINERS).

The dashboard is written for non-experts first. Real = published by NASA/JPL;
Synthetic = simulated by our physics models (contracts 01-05); Placeholder =
fixed stand-in values where a model doesn't exist yet.
"""

from typing import Literal

import streamlit as st

Source = Literal["real", "synthetic", "placeholder"]

# Same blue/orange as the Mission map's real/simulated lines.
BADGES: dict[Source, str] = {
    "real": ":blue-badge[Real · NASA/JPL]",
    "synthetic": ":orange-badge[Synthetic · our simulation]",
    "placeholder": ":gray-badge[Placeholder · not simulated yet]",
}


def data_badge(*sources: Source) -> str:
    """Markdown for one badge per data source, e.g. ``st.markdown(data_badge("real"))``."""
    return " ".join(BADGES[s] for s in sources)


SOURCES: dict[str, tuple[Source, ...]] = {
    "mission.map": ("real", "synthetic"),
    "mission.timeline": ("real",),
    "mission.health": ("synthetic",),
    "mission.link": ("synthetic",),
    "health.temperature": ("synthetic",),
    "health.battery": ("synthetic",),
    "health.power": ("synthetic",),
    "radiation.rate": ("synthetic",),
    "radiation.total": ("synthetic",),
    "radiation.chapters": ("synthetic",),
    "radiation.storm": ("real",),
    "environment.answers": ("real",),
    "environment.particles": ("real",),
    "environment.contact_now": ("real",),
    "environment.windows": ("real",),
    "environment.flyby": ("real",),
    "accuracy.separation": ("real", "synthetic"),
}

SUMMARIES: dict[str, str] = {
    "mission.map": "Earth is in the middle and the grey dashed line is the Moon's path. Blue is "
    "the path Orion really flew; orange is our simulation of it, ending where Orion is now. If the "
    "simulation is right, orange sits on blue.",
    "mission.timeline": "The five stages of the 10-day trip, from NASA's flight plan. The orange "
    "line is the moment shown on this page; hover the diamonds for the engine burns.",
    "mission.health": "A quick check of the spacecraft's simulated systems: temperature, power, "
    "radio and radiation.",
    "mission.link": "Green is when a ground antenna could hear the simulated Orion. Each gap is "
    "colored by its reason, and the orange mark above the bar is the moment shown on this page.",
    "health.temperature": "The electronics must stay inside the green band. If they get too cold, "
    "a heater switches on (red bands).",
    "health.battery": "How full the battery is, like a phone's battery percentage. It drains "
    "when Orion is in shadow (grey bands) and recharges in sunlight.",
    "health.power": "Power from the solar panels versus power the spacecraft uses. When the "
    "orange line is below the grey one, the battery makes up the difference.",
    "radiation.rate": "How fast the dose builds up at one simulated cabin sensor, not the crew's "
    "actual dose. Each step up the scale is 10 times more.",
    "radiation.total": "The dose added up over the flight at one simulated cabin sensor, split by "
    "source. It is not the crew's actual dose.",
    "radiation.chapters": "Where the simulated dose came from, stage by stage. It is a dose at one "
    "cabin sensor, not the crew's actual dose.",
    "radiation.storm": "Real solar particle measurements from the flight. The what-if below them "
    "is a simulation from the Artemis I paper, not an Artemis II event.",
    "environment.answers": "The two short answers for the whole flight, whatever time range is "
    "selected in the sidebar.",
    "environment.particles": "Energetic particles from the Sun, measured near Earth. Inside the "
    "coloured bands counts as a solar radiation storm; the diamonds below are solar events.",
    "environment.contact_now": "NASA talks to Orion through three giant antenna sites around the "
    "world. A site can reach Orion when Orion is above its horizon and the Moon isn't in the way.",
    "environment.windows": "When each site could reach Orion. Red bands are times when no site "
    "could, and the blue band is the planned blackout behind the Moon.",
    "environment.flyby": "As Orion passed behind the Moon, the Moon blocked the radio signal, so "
    "nobody on Earth could reach the crew until it came out the other side.",
    "accuracy.separation": "How many km the simulated Orion is from the real one at the same "
    "moment. Lower is better; a few km over a 400,000 km trip is a very good match.",
}

EXPLAINERS: dict[str, str] = {
    "mission.map": """
**What:** An Earth-centred map of Orion's trip. The dotted rings show distance from Earth.
The wide blue band is the path Orion really flew (NASA/JPL Horizons); the thin orange line
is our digital twin's simulation of it, ending at the orange "Orion is here" dot. The grey
dashed line is the Moon's path over the same time (also JPL Horizons), with the Moon where
it was at the moment shown. The star marks the farthest point from Earth, at the Moon flyby.

**How to read it:** "Top-down" looks down on Earth's North Pole; "3D" can be turned with
the mouse. Scroll to zoom, double-click to reset, hover any point for its time, distance
and speed. The numbers above the map change on every update, because a few km per update
is too small to see on the map. With **Live** off in the sidebar, the replay slider moves
Orion and the Moon along the real path (press Play to watch it), with no simulation needed.

**Why it matters:** This is the whole idea of a digital twin: a simulation that follows the
real spacecraft. The Model accuracy page measures how closely it does.
""",
    "mission.timeline": """
**What:** The flight plan boiled down to five stages: Earth orbit after launch, the trip to
the Moon, the lunar flyby, the trip home, and re-entry with splashdown. The stage changes
at the big engine burns, from NASA's Artemis II overview timeline. Diamonds mark each burn,
the capsule separation, re-entry and splashdown.

**How to read it:** The orange "Now" line is the moment the rest of the page shows: the
simulation's latest moment when Live, the replay time otherwise. Hover a stage or a
diamond for its times. The same stage changes are marked on the Spacecraft health charts.

**Why it matters:** It puts the numbers in context: a battery drain or a temperature dip
means something different in Earth orbit than behind the Moon. The timeline was read off
a graphical PDF and has not been fact-checked yet, so treat times as approximate.
""",
    "mission.health": """
**What:** The latest state of each spacecraft system in plain words, all from our physics
models: temperature, power, the radio link to Earth, and radiation.

**How to read it:** Green means OK; orange or red means a limit from the data contracts
was crossed (for example battery below 20 %). A radio gap caused by where Orion is, out of
view of the ground antennas or behind the Moon, is expected, so it gets a neutral message
instead of a warning. Radiation zones describe where Orion is and are never a warning.

The radiation dose is **simulated absorbed dose in water at one cabin sensor, not the
crew's actual dose**. It is calibrated to Artemis I measurements, and it starts when NASA's
trajectory data starts (Apr 2, 02:00 UTC), so it leaves out the first hours of the flight.

**Why it matters:** Like a car's dashboard warning lights: one look tells you whether
anything needs attention, and the Spacecraft health page shows why.
""",
    "mission.link": """
**What:** The simulated radio link between Orion and NASA's Deep Space Network (DSN) over
the whole mission. Green means connected. A gap means no downlink, for one of these reasons:
out of view of all three DSN sites, blocked by the Moon, no power for the radio, or a
signal too weak to use.

**How to read it:** Hover a gap for its reason, times and length. The simulator checks
visibility every minute, while the coverage chart on Space environment uses hourly real
data, so short gaps can look different there. The simulated Moon blackout (22:43 to 23:23
UTC on Apr 6) is 1 to 2 minutes earlier than NASA's planned window.

**Known limitations:** The model uses the DSN only. The real Orion also used the Near Space
Network close to Earth, so the early simulated gaps overstate its real loss of contact.

**Why it matters:** Gaps are normal in spaceflight. Knowing why one happens separates an
expected loss of signal from a real problem.
""",
    "health.temperature": """
**What:** The temperature of the electronics bay, where Orion's computers and batteries
sit, from our 3-part thermal model of the spacecraft.

**How to read it:** The green band is the safe range from the thermal data contract:
−24 °C (249 K) to 37 °C (310 K). Red bands show when the survival heater was on: it
switches on below −5 °C and off above −3 °C. Grey bands show when the simulated Orion
was in Earth's or the Moon's shadow.

**Why it matters:** In space, the side facing the Sun gets very hot and the shadow side
very cold. The electronics must stay in between, or they stop working.
""",
    "health.battery": """
**What:** How full the battery is (state of charge, %), from our power model.

**How to read it:** The dashed lines are the limits from the power data contract: below
20 % the spacecraft goes into low-power mode, below 10 % it is critical. In shadow (grey
bands) there's no sunlight, so the battery alone powers the spacecraft. The battery size
is a labelled model assumption; NASA doesn't publish Orion's battery specification.

**Why it matters:** The battery keeps Orion alive whenever it can't see the Sun.
""",
    "health.power": """
**What:** Power produced by the four solar-panel wings (orange) and power used by the
spacecraft's systems (grey dashed), in kilowatts.

**How to read it:** Orange above grey: spare power charges the battery. Orange below grey:
the battery covers the shortfall. In shadow the orange line drops to zero. The power used
is a fixed placeholder profile (1.2 kW) until a detailed load model exists.

**Known limitations:** the simulator's Sun direction is still approximate (issue #36),
which affects how much sunlight the panels get and when shadow happens.

**Why it matters:** This balance decides whether the battery fills up or runs down.
""",
    "radiation.rate": """
**What:** The simulated absorbed dose rate in water at one cabin sensor location (HERA HSU2),
in microgray per minute, over the whole trajectory.

**How to read it:** The scale is logarithmic. The tall spikes are the radiation belts near
Earth; the flat line is cosmic rays in deep space. The dark mark is the live or selected moment.

**Known limitations:** The model is calibrated to Artemis I on peak rate and total dose, so
its 287 µGy/min peak matching Artemis I is by construction, not independent evidence. Artemis I
flew a different trajectory and attitude, the model has no real Artemis II attitude or
near-Earth geomagnetic shielding, and no official Artemis II dose data was found.

**Why it matters:** It shows that radiation on this trip comes in short bursts near Earth
and a steady background everywhere else.
""",
    "radiation.total": """
**What:** The simulated absorbed dose in water at one cabin sensor, added up over time and
stacked by source: radiation belts and galactic cosmic rays, in milligray.

**How to read it:** A steep rise is a belt crossing; the slow slope is cosmic rays. The total
counts from the start of NASA's trajectory data, about 3.4 hours after liftoff, and stops
where that data ends before splashdown, so the start and end of the flight are missing.

**Why it matters:** Belts give a large dose quickly, and cosmic rays add up over days. This
**is not the crew's actual dose**: dose varies by location in the spacecraft, and absorbed dose
is not the same as biological risk.
""",
    "radiation.chapters": """
**What:** The simulated dose in three stages of the flight, plus the two moments that shaped
the story: the Moon flyby and the solar storm that didn't happen.

**How to read it:** Leaving Earth runs to the first time Orion is beyond the belts, the long
quiet lasts until it re-enters them, and coming home is the rest. The three doses add up to
the total. The Moon figures come from the geometry of the flight.

**Why it matters:** It explains where the dose came from, and why the Moon that cut the radio
did little to block cosmic rays at this distance.
[Artemis I radiation paper, Nature 634, 48-52 (2024), CC BY 4.0](https://doi.org/10.1038/s41586-024-07927-7)
""",
    "radiation.storm": """
**What:** The highest ≥10 MeV solar proton flux during the flight (NOAA GOES, via NASA iSWA,
a provisional real-time product), compared with NOAA's 10 pfu storm level.

**How to read it:** The what-if uses numbers from the Artemis I paper: a **simulation** of the
October 1989 solar particle event, with peak dose rates of 414 µGy/min at the crew cabin
sensor and 95 µGy/min in the storm shelter. It describes the Artemis I spacecraft and never
happened on Artemis II.

**Why it matters:** A large solar storm is the main radiation danger beyond Earth's magnetic
shield, and it is why Orion has a shelter.
[Artemis I radiation paper, Nature 634, 48-52 (2024), CC BY 4.0](https://doi.org/10.1038/s41586-024-07927-7)
""",
    "environment.answers": """
**What:** Two answers about the whole flight. The first compares the highest flux of
≥10 MeV solar protons (NOAA GOES, via NASA iSWA) with NOAA's solar radiation storm level,
10 pfu. The second is the share of the flight when at least one Deep Space Network site
could reach Orion, from hourly JPL Horizons geometry minus NASA's planned Moon blackout.

**How to read it:** "No solar radiation storm" is about energetic particles only. NASA's
DONKI database also lists geomagnetic storms during the flight. Those are disturbances of
Earth's magnetic field, a different kind of storm, shown in the event strip below. GOES
data is NOAA's provisional real-time product.

**Why it matters:** A solar particle storm is the main radiation danger beyond Earth's
magnetic shield, and contact with Earth is how the crew gets support.
""",
    "environment.flyby": """
**What:** The communications blackout while Orion passed behind the Moon on April 6.

**How to read it:** The times are NASA's **planned** window, 6:44 to 7:25 p.m. EDT (22:44
to 23:25 UTC). NASA's flight log reports the signal returning around 7:24 p.m. EDT, without
an exact time. Our simulation, on the Mission page, puts its blackout at 22:43 to 23:23 UTC,
1 to 2 minutes earlier. This page stays with NASA's published times because it shows real
data only.

**Why it matters:** The antenna geometry alone says Canberra could reach Orion, because
Orion was high above its horizon. Only the Moon stood in the way.
[NASA flight day 6 updates](https://www.nasa.gov/blogs/missions/2026/04/06/artemis-ii-flight-day-6-lunar-flyby-updates)
""",
    "environment.particles": """
**What:** The top chart is the flux of high-energy protons (≥10 MeV) from the Sun,
measured by NOAA's GOES satellites near Earth, via NASA iSWA. The strip below marks solar
events recorded by NASA's DONKI database: eruptions (CMEs), flares, storms. The light blue
background is the time Orion was flying.

**How to read it:** The scale is logarithmic: each step up is 10× more particles. The
coloured bands are NOAA's solar radiation storm levels, defined on exactly this
measurement: 10 particle-flux units (pfu) is a minor storm (S1), 100 is moderate (S2),
1000 is strong (S3). Hover a diamond for the event's details.

**Why it matters:** Solar particle storms are the main radiation danger for astronauts
beyond Earth's magnetic shield. A storm during the flight would be the radiation story of
the mission.
""",
    "environment.contact_now": """
**What:** Whether each of NASA's three Deep Space Network sites (Goldstone in California,
Madrid in Spain, Canberra in Australia) could see Orion at the current moment of the
simulation.

**How to read it:** "Can reach Orion" means Orion was at least 10° above that site's
horizon. That cutoff is a model assumption chosen in this project (low over the horizon
the signal passes through more air), not an official DSN rule. The positions are real
geometry from JPL Horizons, in hourly steps. During NASA's planned Moon blackout, a site
with Orion above its horizon shows "Blocked by the Moon". The signal time is Horizons' one-way light
time: radio travels at the speed of light, about 300,000 km per second, so near the Moon
a message needs over a second each way.

**Why it matters:** The three sites are spread around the globe so that, as Earth turns,
at least one of them can usually talk to the spacecraft. The delay is why anything that needs
a split-second reaction is handled on board, by the crew or Orion's computers, not from Earth.
""",
    "environment.windows": """
**What:** For each antenna site, the stretches of time when it could reach Orion
(coloured bars), during the selected time range.

**How to read it:** Bars from different sites take turns as Earth rotates. Red bands mark
times when no site could reach Orion, which is when the spacecraft would have to store its
data until contact returns. The blue band is NASA's planned Moon blackout, the only edge
here with minute precision. The orange line is the current moment. The other bar edges come
from hourly data, so they are accurate to about an hour, and short gaps can look different
from the minute-by-minute simulation on the Mission page.

**Why it matters:** It shows how continuous contact with the crew was.
""",
    "accuracy.separation": """
**What:** At each hour where both exist, the straight-line distance between where our
simulation puts Orion and where NASA/JPL says Orion really was.

**How it's computed:** Real positions are JPL Horizons vectors (hourly, Earth mean
equator J2000 / EME2000, UT). Each is paired with the simulated tick (1 Hz, EME2000, UTC)
nearest in time, within 30 s. The simulation interpolates NASA's own OEM trajectory files,
so a correct pipeline should stay within a few km. A sudden jump usually means a frame or
time-stamp mismatch (both documented as Horizons gotchas in CLAUDE.md) rather than physics.

**Why it matters:** Every other simulated number (sunlight, temperature, power) is built on
top of this trajectory, so it has to be right first.
""",
}


def explain(key: str) -> None:
    """Render a chart's data-source badges, its one-line summary, and the
    "About this chart" expander."""
    sources = SOURCES.get(key)
    summary = SUMMARIES.get(key)
    if sources or summary:
        st.markdown(" ".join(p for p in (data_badge(*(sources or ())), summary) if p))
    text = EXPLAINERS.get(key)
    if text:
        with st.expander("About this chart"):
            st.markdown(text)
