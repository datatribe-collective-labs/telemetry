# Timeline fact-check checklist: `planned_attitude.py` vs Overview-Timeline PDF

**How to use:** Open `docs/overview/artemis-ii-overview-timeline-public-final.pdf` (pages 1–3)
side by side with this list. For each row, verify in the PDF: (a) the **flight-day grid cell
exists**, (b) the **start/end MET** matches the grid or its printed time, (c) the **mode/label**
text matches. Tick when verified; if wrong, write the correct value in the row (I'll apply it).
Rows are generated mechanically from `planned_attitude.py` — no transcription drift possible.

**Known structural issues found programmatically (start here):**
- ⚠️ Gap: segment ends 0/05:00, next starts 0/05:02
- ⚠️ Gap: segment ends 0/10:00, next starts 0/10:06
- ⚠️ **Out of order**: segment idx 17 ends at 1/00:00 but the next starts 0/17:00 (7 h backward jump)

**Verified anchors (cross-check these first — they pin the whole grid):**

| Event | MET per code | Anchor source |
|---|---|---|
| ICPS Spring Sep | 0/03:24 | text label in PDF |
| ICPS Disposal Burn | 0/05:02 | text label |
| Orion TLI | ~1/01:37 | text label |
| OTC-1 / OTC-2 / OTC-3 | 2/00:07, 3/00:12, 4/05:23 | text labels |
| Lunar SOI Entry | 4/06:59 | text label |
| Lunar Close Approach | 5/01:23:20 | text label |
| Max Earth Distance | 5/01:26:57 | text label |
| Lunar SOI Exit | 5/19:47 | text label |
| EI / Splashdown | 9/01:33 / 9/01:46 | text labels |

## Segments (108 rows)

| # | MET start | MET end | Mode (code) | Description (code) | ✓/✗ + correction |
|---|-----------|---------|-------------|--------------------|-------------------|
| 0 | 0/00:00 | 0/01:00 | `PRELAUNCH` | Prelaunch to Ascent: Not applicable prior to orbital insertion | ☐ |
| 1 | 0/01:00 | 0/01:48 | `T_ROLL_MNVRS` | Tail-Roll Maneuvers | ☐ |
| 2 | 0/01:48 | 0/02:00 | `BURN_ARB` | ARB TIG 0/01:48 | ☐ |
| 3 | 0/02:00 | 0/03:24 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 4 | 0/03:24 | 0/03:30 | `SEP` | ICPS Spring Sep 0/03:24 | ☐ |
| 5 | 0/03:30 | 0/05:00 | `POD_ATT` | Proximity Operations Demo | ☐ |
| 6 | 0/05:02 | 0/05:30 | `SEP` | ICPS Disposal Burn 0/05:02 | ☐ |
| 7 | 0/05:30 | 0/08:30 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 8 | 0/08:30 | 0/09:00 | `DFTO_ATTITUDE` | DFTO attitude | ☐ |
| 9 | 0/09:00 | 0/10:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 10 | 0/10:06 | 0/11:00 | `OPCOMM` | OpComm Intl Act 0/10:06 | ☐ |
| 11 | 0/11:00 | 0/12:30 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 12 | 0/12:30 | 0/13:45 | `SFM` | Pre-burn setup | ☐ |
| 13 | 0/13:45 | 0/14:00 | `BURN_PRB` | Orion PRB 0/13:45 | ☐ |
| 14 | 0/14:00 | 0/14:15 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 15 | 0/14:15 | 0/15:00 | `OPNAV` | OpNav C/O | ☐ |
| 16 | 0/15:00 | 0/15:30 | `SFM` | Pre-burn setup | ☐ |
| 17 | 0/15:30 | 1/00:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 18 | 0/17:00 | 1/00:30 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 19 | 1/00:30 | 1/01:00 | `DOCK_CAM` | Dock Cam pointing | ☐ |
| 20 | 1/01:00 | 1/01:15 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 21 | 1/01:15 | 1/01:37 | `SFM` | Pre-TLI setup | ☐ |
| 22 | 1/01:37 | 1/02:00 | `BURN_TLI` | Orion TLI 01/01:37 | ☐ |
| 23 | 1/02:00 | 1/08:30 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 24 | 1/08:30 | 1/14:00 | `SURVEY_ATT` | CM/SM Survey 01/12:00 | ☐ |
| 25 | 1/14:00 | 1/17:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 26 | 1/17:00 | 1/21:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 27 | 1/21:00 | 1/22:00 | `OPNAV` | OpNav pointing | ☐ |
| 28 | 1/22:00 | 1/22:30 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 29 | 1/22:30 | 1/23:30 | `SFM` | Pre-OTC-1 setup | ☐ |
| 30 | 1/23:30 | 2/00:07 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 31 | 2/00:07 | 2/00:30 | `BURN_OTC` | OTC-1 02/00:07 | ☐ |
| 32 | 2/00:30 | 2/05:30 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 33 | 2/05:30 | 2/07:00 | `FTO_ATTITUDE` | FTO attitude (Emergency Comm DFTO, SAW Shadow Test) | ☐ |
| 34 | 2/07:00 | 2/08:30 | `DOCK_CAM` | Dock Cam pointing | ☐ |
| 35 | 2/08:30 | 2/10:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 36 | 2/10:00 | 2/11:00 | `DFTO_ATTITUDE` | DFTO attitude | ☐ |
| 37 | 2/11:00 | 2/13:30 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 38 | 2/13:30 | 2/14:30 | `DFTO_ATTITUDE` | DFTO attitude | ☐ |
| 39 | 2/14:30 | 2/17:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 40 | 2/17:00 | 2/21:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 41 | 2/21:00 | 2/22:00 | `OPNAV` | OpNav pointing | ☐ |
| 42 | 2/22:00 | 2/22:45 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 43 | 2/22:45 | 2/23:30 | `SFM` | Pre-OTC-2 setup | ☐ |
| 44 | 2/23:30 | 3/00:12 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 45 | 3/00:12 | 3/00:30 | `BURN_OTC` | OTC-2 03/00:12 | ☐ |
| 46 | 3/00:30 | 3/02:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 47 | 3/02:00 | 3/04:00 | `DFTO_ATTITUDE` | DFTO attitude (Acoustic DFTO, OpComm CFDP Demo) | ☐ |
| 48 | 3/04:00 | 3/06:30 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 49 | 3/06:30 | 3/07:30 | `FTO_ATTITUDE` | FTO attitude (Internal Demo FTOs) | ☐ |
| 50 | 3/07:30 | 3/08:30 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 51 | 3/08:30 | 3/09:30 | `DFTO_ATTITUDE` | DFTO attitude (Dock Cam Stray Light, Misalignment) | ☐ |
| 52 | 3/09:30 | 3/13:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 53 | 3/13:00 | 3/15:00 | `DFTO_ATTITUDE` | DFTO attitude (Dock Cam Misalignment) | ☐ |
| 54 | 3/15:00 | 3/17:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 55 | 3/17:00 | 3/21:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 56 | 3/21:00 | 3/22:00 | `OPNAV` | OpNav pointing | ☐ |
| 57 | 3/22:00 | 3/23:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 58 | 3/23:00 | 4/04:30 | `SFM` | Pre-OTC-3 setup | ☐ |
| 59 | 4/04:30 | 4/05:23 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 60 | 4/05:23 | 4/06:00 | `BURN_OTC` | OTC-3 04/05:23 | ☐ |
| 61 | 4/06:00 | 4/08:30 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 62 | 4/08:30 | 4/10:30 | `DFTO_ATTITUDE` | DFTO attitude (OpComm ANU Demo, Dock Cam Misalignment) | ☐ |
| 63 | 4/10:30 | 4/17:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 64 | 4/17:00 | 4/23:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 65 | 4/23:00 | 5/03:00 | `OBSV` | Close Approach 05/01:23 | ☐ |
| 66 | 5/03:00 | 5/04:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 67 | 5/04:00 | 5/08:30 | `SURVEY_ATT` | CM/SM Survey 05/12:45 | ☐ |
| 68 | 5/08:30 | 5/17:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 69 | 5/17:00 | 5/21:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 70 | 5/21:00 | 5/22:00 | `OPNAV` | OpNav pointing | ☐ |
| 71 | 5/22:00 | 6/00:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 72 | 6/00:00 | 6/04:00 | `SFM` | Pre-RTC-1 setup | ☐ |
| 73 | 6/04:00 | 6/04:23 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 74 | 6/04:23 | 6/05:00 | `BURN_RTC` | RTC-1 06/04:23 | ☐ |
| 75 | 6/05:00 | 6/06:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 76 | 6/06:00 | 6/07:00 | `FTO_ATTITUDE` | FTO attitude | ☐ |
| 77 | 6/07:00 | 6/08:00 | `FTO_WW_VIEW` | FTO Window View | ☐ |
| 78 | 6/08:00 | 6/10:30 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 79 | 6/10:30 | 6/17:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 80 | 6/17:00 | 7/04:30 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 81 | 7/04:30 | 7/06:30 | `DFTO_ATTITUDE` | DFTO attitude (Urine Venting, No PCD DFTOs) | ☐ |
| 82 | 7/06:30 | 7/08:30 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 83 | 7/08:30 | 7/10:30 | `DFTO_ATTITUDE` | DFTO attitude (COGN Test, Urine/Toilet Demo, Radiation Shelter, Manual Piloting) | ☐ |
| 84 | 7/10:30 | 7/12:30 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 85 | 7/12:30 | 7/14:00 | `DFTO_ATTITUDE` | DFTO attitude | ☐ |
| 86 | 7/14:00 | 7/15:30 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 87 | 7/15:30 | 7/17:00 | `BIAS_NEG_XSI_MITIGATE_X` | Bias -XSI Mitigate X | ☐ |
| 88 | 7/17:00 | 7/20:00 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 89 | 7/20:00 | 7/22:00 | `DFTO_ATTITUDE` | DFTO attitude | ☐ |
| 90 | 7/22:00 | 7/23:30 | `BIAS_NEG_XSI_MITIGATE_X` | Bias -XSI Mitigate X | ☐ |
| 91 | 7/23:30 | 8/01:00 | `OPNAV` | OpNav pointing | ☐ |
| 92 | 8/01:00 | 8/02:30 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 93 | 8/02:30 | 8/04:00 | `SFM` | Pre-RTC-2 setup | ☐ |
| 94 | 8/04:00 | 8/04:33 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 95 | 8/04:33 | 8/05:00 | `BURN_RTC` | RTC-2 08/04:33 | ☐ |
| 96 | 8/05:00 | 8/17:00 | `BIAS_NEG_XSI_MITIGATE_X` | Bias -XSI Mitigate X | ☐ |
| 97 | 8/17:00 | 8/19:00 | `OPNAV` | OpNav pointing | ☐ |
| 98 | 8/19:00 | 8/19:45 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 99 | 8/19:45 | 8/20:15 | `SFM` | Pre-RTC-3 setup | ☐ |
| 100 | 8/20:15 | 8/20:33 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 101 | 8/20:33 | 8/21:00 | `BURN_RTC` | RTC-3 08/20:33 | ☐ |
| 102 | 8/21:00 | 8/23:30 | `BIAS_NEG_XSI_MITIGATE_X` | Bias -XSI Mitigate X | ☐ |
| 103 | 8/23:30 | 9/00:30 | `SFM` | Pre-entry setup | ☐ |
| 104 | 9/00:30 | 9/01:13 | `BIAS_NEG_XSI` | Bias -XSI | ☐ |
| 105 | 9/01:13 | 9/01:33 | `SEP` | CM/SM Sep 09/01:13 | ☐ |
| 106 | 9/01:33 | 9/01:46 | `EDL` | Entry Interface 09/01:33 to Splashdown 09/01:46 | ☐ |
| 107 | 9/01:46 | 9/02:00 | `RECOVERY` | Splashdown / Recovery | ☐ |
