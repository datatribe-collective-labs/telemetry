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
    "mission.health": ("synthetic", "placeholder"),
    "health.temperature": ("synthetic",),
    "health.battery": ("synthetic",),
    "health.power": ("synthetic",),
    "environment.particles": ("real",),
    "environment.contact_now": ("real",),
    "environment.windows": ("real",),
    "accuracy.separation": ("real", "synthetic"),
}

SUMMARIES: dict[str, str] = {
    "mission.map": "Earth is in the middle and the grey dashed line is the Moon's path. Blue is "
    "the path Orion really flew; orange is our simulation of it, ending where Orion is now. If the "
    "simulation is right, orange sits on blue.",
    "mission.timeline": "The five stages of the 10-day trip, from NASA's flight plan. The orange "
    "line is the moment shown on this page; hover the diamonds for the engine burns.",
    "mission.health": "A quick check of the spacecraft's systems. Grey means we don't simulate "
    "that system yet.",
    "health.temperature": "The electronics must stay inside the green band. If they get too cold, "
    "a heater switches on (red bands).",
    "health.battery": "How full the battery is, like a phone's battery percentage. It drains "
    "when Orion is in shadow (grey bands) and recharges in sunlight.",
    "health.power": "Power from the solar panels versus power the spacecraft uses. When the "
    "orange line is below the grey one, the battery makes up the difference.",
    "environment.particles": "Energetic particles from the Sun, measured near Earth. Inside the "
    "coloured bands counts as a solar radiation storm; the diamonds below are solar events.",
    "environment.contact_now": "NASA talks to Orion through three giant antenna sites around the "
    "world. A site can only reach Orion when Orion is above its horizon.",
    "environment.windows": "When each site could reach Orion. Red bands are times when no site "
    "could.",
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
**What:** The latest state of each spacecraft system in plain words: temperature and power
from our physics models, plus the radio link and radiation, which we don't simulate yet.

**How to read it:** Green means OK; orange or red means a limit from the data contracts
was crossed (for example battery below 20 %). Grey means "not simulated yet": those
models are being built by other contributors. Real antenna and particle data is on the
Space environment page.

**Why it matters:** Like a car's dashboard warning lights: one look tells you whether
anything needs attention, and the Spacecraft health page shows why.
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
geometry from JPL Horizons, in hourly steps. The signal time is Horizons' one-way light
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
data until contact returns. The orange line is the current moment. Hourly data, so bar
edges are accurate to about an hour.

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
