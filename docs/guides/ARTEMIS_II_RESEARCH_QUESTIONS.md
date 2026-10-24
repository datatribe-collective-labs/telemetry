# Prompt for ChatGPT: Artemis II / Orion Research for the Digital Twin

**How to use:** paste the sections below into ChatGPT (or similar) — ideally one section per
conversation so answers can stay detailed. Ask for **sources with URLs** for every factual
claim and for a clear **"unverified"** flag on anything the model cannot source. Feed
answers back into this file (append at the bottom) or into a new doc and tell the agent
where they landed.

Context for the AI: *"We are building an open-source digital twin of the NASA Artemis II /
Orion spacecraft telemetry. We validate physics-model contracts (ODCS v3) and dashboards.
Answer with engineering numbers, units, and cite public sources (NASA SLS Reference Guide,
JPL Horizons, DSN 810-005 handbook, ESA Orion ESM documentation, A.T.L.A.S,
track-artemis.com, NASA press kits). Mark anything you cannot source as UNVERIFIED."*

---

## Section 1 — Artemis II flight profile & lunar flyby (for trajectory visualization)

1. Complete mission timeline with approximate MET (mission elapsed time) for each event:
   launch, ICPS separation, solar array deploy, outbound powered flyby (if flown),
   high Earth orbit period/apogee/perigee, TLI burn time & duration, translunar coast
   duration, lunar flyby (closest approach time), return coast, entry, splashdown.
2. Lunar flyby geometry: closest-approach distance from the lunar surface (km),
   altitude over the far side, flyby date relative to launch (mission day).
3. Free-return trajectory: confirm Artemis II flies a free-return profile (vs hybrid),
   expected total mission duration (~10 days?), maximum Earth distance (~km).
4. High Earth orbit (post-launch checkout) parameters: apogee/perigee altitudes,
   period, number of orbits before TLI.
5. Expected eclipse periods (Earth shadow) during the mission and their durations.
6. Entry interface speed (km/s) and entry flight path angle.
7. Any public OEM/Horizons ephemeris for Artemis II (Horizons target id -1024):
   coverage start (ICPS separation?), time step, end.
8. Where are the "big burns" (OPF/TLI/RB burns) located and their approximate delta-V.

## Section 2 — Orion electrical power system (for power model validation)

1. Solar array: number of wings, span, total area (m²), wing area, BOL power (kW),
   operating voltage, cell type (triple-junction GaAs?), efficiency.
2. Batteries: number, chemistry, capacity (Ah / kWh), nominal bus voltage.
3. Typical loads (W) if published: avionics, life support, heaters, comms transmitter.
4. Confirmed figures: 4 wings / ~11.2 kW appears on track-artemis.com (A.T.L.A.S) —
   corroborate or correct with NASA/ESA sources.

## Section 3 — Orion communications (for comms model validation — partner scope, but bounds matter)

1. Downlink bands used: S-band (2.2–2.3 GHz?) and Ka-band? Which rates are published?
2. Typical downlink data rates for Artemis II (video streaming demonstrations).
3. Which network handles Artemis II: DSN, Near Space Network (TDRS), ESA tracking?
4. DSN 34-m BWG antenna S-band G/T and gain (from 810-005 modules 101/104/206).

## Section 4 — Orion thermal control (for thermal model validation)

1. What is publicly known about Orion's thermal control system: radiators, MLI,
   heater zones, fluid loops (if any), typical temperatures.
2. Any public qualification temperature ranges for Orion avionics/electronics bays.
3. Solar array operating temperature range and temperature coefficient (%/°C).

## Section 5 — Contract physics sanity checks

1. Solar constant: IAU 2015 value 1361 W/m² — confirm; expected range at
   0.995–1.005 AU (we compute 1347.7–1374.4 W/m² — verify).
2. Light time at 410,000 km: we compute 1.368 s one-way (contract says ~1.38 s) — verify.
3. Orion stack mass ~25,848 kg and cross-sectional area ~33.2 m² — verify or correct.
4. DSN elevation mask: is 10° the correct operational cutoff for S-band DSN tracks?
5. Artemis II mission window: April 2026 Earth distance from Sun ~0.9986 AU — verify
   with an ephemeris source.

---

## Answers (paste back here)

> Pending ChatGPT answers for comms/thermal/EPS details. However, on 2026-10-19 the user
> supplied **official NASA documents** that already answer most of Sections 1 & 5 —
> transcribed below.

### From `data/oem/all-artemis-ii-oem-files.zip` (NASA/JSC/FOD/FDO CCSDS OEM v2.0 files)

10 planning arcs (2026-04-02 → 04-10), each `EM2`, Earth-centered **EME2000**, `TIME_SYSTEM = UTC`,
position km / velocity km/s. Latest planning arc analyzed: `Artemis_II_OEM_2026_04_09_Post-ICPS-Sep_to_EI.asc`
(3,259 state vectors, 2026-04-02T01:57:37Z → 2026-04-10T23:53:30Z, nominal 240 s cadence,
matches contract-01 "OEM cadence 4 min"):

| Metric | Value | Time (UTC) |
|--------|-------|-----------|
| Min Earth range (entry interface) | **6,499 km** | 2026-04-10 23:53:30 |
| Max Earth range (≈ lunar flyby) | **413,144 km** | 2026-04-06 23:02:52 |
| Max speed (entry) | **10.999 km/s** | 2026-04-10 23:53:30 |
| Min speed (apogee/flyby) | **0.414 km/s** | 2026-04-06 23:26:52 |

Cross-checks against contract 01: max distance 413,144 km ✓ matches the contract's noted value;
entry speed 10.999 ≈ the contract's ~11 km/s ceiling ✓; OEM begins ~3.4 h after configured liftoff
(2026-04-01T22:35Z) = post-ICPS separation ✓ ("OEM data begins at ICPS separation").

### From `artemis-ii-overview-timeline-public-final.pdf` (official overview timeline)

Event METs (flight-day format D/HH:MM, liftoff = MET 0 ≈ 2026-04-01T22:35Z per config):

| MET | Event |
|-----|-------|
| 0/03:24 | Orion/ICPS Spring Separation |
| 0/05:02 | ICPS Disposal Burn |
| 0/05:27 | SPL deploys |
| 0/10:06 | OpComm initial activation |
| 0/13:45 | Orion PRB |
| ~01/01:37 | **Orion TLI** (matches contract eclipse note MET 25.7 h) |
| 01/12:00 | CM/SM survey |
| 02/00:07 | OTC-1 (outbound trajectory correction) |
| 3/00:12 | OTC-2 |
| 4/05:23 | OTC-3 |
| 4/06:59 | **Lunar SOI entry** |
| **5/01:23:20** | **Lunar close approach** |
| 5/01:26:57 | **Max Earth distance** (413,144 km per OEM) |
| 5/19:47 | Lunar SOI exit |
| 7/17:30 | FCS checkouts |
| 8/04:33 | RTC-2 |
| 8/20:33 | RTC-3 |
| 09/01:13 | CM/SM separation |
| 09/01:33 | Entry interface |
| 09/01:46 | **Splashdown** (≈ 9 d 1 h 46 m mission) |

Note the two lunar numbers differ by 3.5 min — close approach vs max-Earth-distance are
distinct events; the OEM independently places max range at 2026-04-06T23:02Z.

### Still open for ChatGPT
Section 2 (EPS: wings/area/battery), Section 3 (comms bands/rates/network), Section 4
(thermal control public data), and Section 5 items 1–5 (source confirmations).

---

## Update 2026-10-19 (post-implementation): new questions & suspected contract errors

Work after the first audit (see `docs/integration/CONTRACT_PHYSICS_AUDIT.md`) surfaced
more things to verify. **ANSWERED by ChatGPT on 2026-10-19** — see §"ChatGPT answers,
vetted" below; the questions are kept for provenance.

### New facts established from the OEM data (no ChatGPT needed)
- OEM arcs are planning revisions: 9 of 10 members are CCSDS OEM v2.0; the 10th
  ("2026.04.10 - Post-RTC3 to EI") is a legacy **PROP_MAN 11.0** entry arc with epochs in
  M50-referenced seconds and **FT/FPS units** — confirmed by inspection; it is skipped by
  our ingests. If the entry-arc data is ever needed, ask ChatGPT: *"How to interpret an
  STK 'PROP_MAN 11.0' ephemeris header line `2026 7857312.084 782298.782 817.975 M50 FT
  FPS SEC` — what is the epoch reference and how to convert to UTC/EME2000 km?"*
- Entry interface in OEM: speed 10.999 km/s at range 6,499 km — the contract's "~10.97
  km/s / 39,490 km/h" statement is slightly off (39,490 km/h = 10.969 km/s). Suspected
  small error in contract 01 text; ask ChatGPT to confirm Artemis II EI speed ~11.0 km/s
  against NASA sources.

### Suspected contract 02 (thermal) issues to verify
1. Heater setpoint appears internally contradictory in contract 02 (limitations say
   −5 °C/268 K; some text treats 268 K as unverified assumption). We standardized on
   **268.15 K** and 25 W as MODEL_ASSUMPTION. Ask ChatGPT: *"Is there any public source
   for an Orion survival-heater setpoint or heater power rating? If none, confirm this
   must remain a model assumption."*
2. The 249–310 K band is explicitly an **SLS flight-computer** spec, not Orion bay
   qualification. Ask: *"Do any public Artemis/Orion sources give electronics or battery
   bay temperature limits, or should the contract keep 249–310 K clearly labeled as an
   SLS-avionics reference?"*

### Suspected contract 03 (power) issues to verify
1. We switched the implementation to **44.8 m² / 28% BOL** (4 wings) because the
   contract's physics ceiling 17,100 W is derived from those numbers — but the contract
   also says 44.8 m² and 28% are NOT independently verified. Ask ChatGPT: *"Confirm Orion
   ESM solar array: 4 wings, wing dimensions (~5.2 m each?), total area, BOL power (is
   11.2 kW at a specific point?) from ESA/NASA sources."*
2. Battery: implementation assumes **100 Ah, 28 V**. Contract calls this unverified.
   Ask: "Orion battery chemistry, capacity, and nominal bus voltage from public sources."
3. Available-power semantics: contract text says "available above essential loads
   (800 W floor); negative = CRITICAL" but implementation computes array + max discharge
   capability. Ask: "Is there any published Orion EPS essential-load figure? If not,
   we should rewrite the contract text to say the 800 W floor is a model assumption."

### Timeline (planned_attitude.py) fact-check task
The extracted timeline (`ATTITUDE_TIMELINE`, 108 segments) has **not been validated
against the PDF**. Ask ChatGPT to assist with the review pattern: *"Given this segment
list (paste) and the official Artemis II Overview Timeline events (ICPS Sep 0/03:24,
TLI ~01/01:37, OTC-1 02/00:07, OTC-2 3/00:12, OTC-3 4/05:23, Lunar SOI entry 4/06:59,
close approach 5/01:23:20, SOI exit 5/19:47, EI 09/01:33, splashdown 09/01:46), flag
any segment whose boundaries/modes conflict with these anchor events."* Mark mismatches
back in `planned_attitude.py` and re-run `pipelines.ingest.mission_events`.

### Other loose ends to confirm
- Contract 01 says eclipse model has "no penumbra" but the enum includes PENUMBRA and the
  implementation models it; contract text probably mistaken. Ask ChatGPT for a sanity
  check on angular-shadow eclipse conventions if you want external support.
- "Max Earth distance 406,773 km" (contract 01 x_km discussion) vs measured OEM max
  range **413,144 km** — contract contains both numbers; one likely refers to
  center-to-surface vs center-to-center. Ask ChatGPT to confirm which is the quoted
  Artemis II record distance and correct the contract text accordingly.

---

## ChatGPT answers, vetted (received 2026-10-19)

ChatGPT's full response is summarized below with a verification status for each
claim. Method: claims that affect code/contracts were checked first-hand before
encoding — ESA pages fetched directly (✅), internal consistency recomputed in-repo
(✅), otherwise marked **ChatGPT-cited** (source named by ChatGPT, not refetched by us)
or **UNVERIFIED**.

### Verification log (independent checks done in this repo)

| ChatGPT claim | Our check | Result |
|---|---|---|
| ESM: 4 wings × 3 panels (2130×1920 mm), 11.2 kW, GaAs triple-junction (Emcore), 120 V distribution | Fetched ESA "ESM: Power" page directly | ✅ Confirmed verbatim |
| ESM thermal: 6 radiators (4 full, 2 split), 2 loops, HFE-7200, cold plates, MLI, heaters | Fetched ESA "ESM: Temperature control" page directly | ✅ Confirmed verbatim |
| Panel-envelope area 12×2.130×1.920 = 49.08 m² | Recomputed | ✅ — note this is envelope, not active cell area |
| Timeline MET/UTC drift: close approach MET 5/01:23:20 + liftoff 22:35Z = Apr 6 23:58Z vs OEM max-range 23:02:52Z | Recomputed from repo config + OEM | ✅ Confirmed (~59 min drift); ICPS-Sep anchor is consistent (OEM start ≈ liftoff+3:24). **Conclusion: the OEM arc is the temporal ground truth for trajectory; timeline-METs drift in translunar coast — treat planned_attitude times as approximations (±1 h), do not "fix" timestamps** |
| NASA press: closest lunar approach ≈ 6,545 km above surface; max Earth distance 252,756 mi ≈ 406,771 km; ~40 min blackout; ~1 h flyby eclipse | ChatGPT-cited (NASA FD6 report; NASA pages not fetchable here) | ⚠️ Accepted with attribution; note 406,771 = **surface** distance vs our OEM geocentric range 413,144 km — difference ≈ Earth radius (6,371 km), internally consistent, so the geometric explanation checks out numerically |
| S-band max ~<6 Mbps; optical O2O up to 260 Mbps; NSN+DSN both used | ChatGPT-cited (NASA O2O pages) | ⚠️ ChatGPT-cited; O2O optical rate is NOT an RF rate — comms model must keep them separate |
| "Hybrid free-return" (not pure free-return) trajectory | ChatGPT-cited (NASA/NTRS trajectory paper, link 404 here) | ⚠️ ChatGPT-cited |
| DSN 10° elevation mask "not a universal rule" | Plausible, matches contract's own cautious wording | ⚠️ keep as configurable assumption (current model default) |
| 2026 NTRS paper on Orion ATCS (2 CM loops, PCM, ammonia boilers unused until SM sep) | ChatGPT-cited | ⚠️ ChatGPT-cited |

### Resolved by these answers (action applied / needed)

1. **EPS:** array = 11.2 kW peak, 4 wings/12 panels, 120 V distribution (ESA ✅).
   Our model keeps 44.8 m²/0.28 as MODEL_ASSUMPTION pair that reproduces the 17.1 kW
   contract ceiling; the 11.2 kW design point corresponds to realistic losses (≈0.65
   combined derating) — fine. **Battery 100 Ah / 28 V stays MODEL_ASSUMPTION** and the
   ESA 120 V figure is array distribution, NOT battery bus (contract text should not
   imply otherwise). TODO: add that one clause to contract 03 battery_voltage description.
2. **Thermal:** architecture matches (radiators/loops/heaters/MLI ✅). 268.15 K setpoint
   and 25 W heater stay MODEL_ASSUMPTION (contract already says so); 249–310 K stays
   labeled as SLS-avionics reference only (contract already does).
3. **Contract 01 text corrections applied:** entry speed note '~10.97 km/s (39,490 km/h)'
   → '~11.0 km/s (OEM arc 2026-04-09: 10.999 km/s at EI)'; the 413,144 km attribution was
   wrong ("post-splashdown arc") → corrected to "geocentric range, lunar flyby arc".
   The 406,773 km figure = NASA's Earth-surface distance — definition-clause added instead
   of deletion; recommend a future field split (center range vs surface distance).
4. **DSN 10° mask** remains a config default assumption (both the contract and ChatGPT agree).
5. **Solar flux bounds** 1347–1375 W/m² in contract 01 stand (recomputed exact values
   1347.49/1374.71 fall inside as rounded bounds; ChatGPT's nitpicked "1347.49–1374.71"
   is what the contract's rule-based check already enforces approximately).
6. **Light time** 1.368 s at 410,000 km confirmed; contract's "~1.38 s" acceptable as a
   rounded bound statement (rule `|lt − d/c| < 0.01 s` is the enforceable part).

### Still UNVERIFIED (do not put into contracts as specs)

Orion battery chemistry/capacity/voltage; essential-load 800 W; heater setpoint/rating;
Orion bay qualification temps; array active area/efficiency/temp coefficient; RF
frequencies & Ka rates; config-specific DSN gain/G/T; stack mass 25,848 kg; cross-section
33.2 m²; April 2026 Earth–Sun distance 0.9986 AU (compute from ephemeris instead); burn
delta-Vs/durations; Horizons -1024 exact coverage.
