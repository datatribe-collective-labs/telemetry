"""Artemis II Planned Attitude Profile from Mission Timeline.

Maps Mission Elapsed Time (MET) to planned attitude modes per the
Artemis II Overview Timeline (public final). Attitude modes must be
translated to quaternions/Euler angles by the state engine using
Orion operations concepts.

Source: NASA Artemis II Overview Timeline - FINAL (January 8, 2026)
Canonical truth model: 107 verified attitude cells across FD01-FD10
"""

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum


class AttitudeMode(str, Enum):
    """Planned attitude modes from the mission timeline (canonical PDF truth model)."""

    # Default coast attitude (dominant mode)
    BIAS_NEG_XSI = "BIAS_NEG_XSI"
    BIAS_NEG_XSI_MITIGATE_X = "BIAS_NEG_XSI_MITIGATE_X"

    # Burns - thrust-vector-aligned (canonical names from PDF)
    BURN_ARB = "BURN_ARB"           # Ascent Abort / ARB
    BURN_PRB = "BURN_PRB"           # Perigee Raise Burn
    BURN_TLI = "BURN_TLI"           # Trans-Lunar Injection
    BURN_OTC = "BURN_OTC"           # Outbound Trajectory Correction (OTC-1,2,3)
    BURN_RTC = "BURN_RTC"           # Return Trajectory Correction (RTC-1,2,3)

    # Pre-burn setup / maneuver
    SFM = "SFM"                     # Pre-burn setup / Final Maneuver

    # Separation
    SEP = "SEP"                     # CM/SM Separation

    # Entry phases
    EDL = "EDL"                     # Entry Interface to Splashdown
    RECOVERY = "RECOVERY"           # Post-splashdown recovery

    # Maneuvers / Demos
    T_ROLL_MNVRS = "T_ROLL_MNVRS"
    POD_ATT = "POD_ATT"
    SURVEY_ATT = "SURVEY_ATT"
    DOCK_CAM = "DOCK_CAM"
    OPNAV = "OPNAV"
    OPCOMM = "OPCOMM"
    OBSV = "OBSV"

    # FTO / DFTO specific
    FTO_ATTITUDE = "FTO_ATTITUDE"
    FTO_WW_VIEW = "FTO_WW_VIEW"
    DFTO_ATTITUDE = "DFTO_ATTITUDE"

    # Legacy combined entry (for backward compatibility)
    ENTRY_ATTITUDE = "ENTRY_ATTITUDE"

    # Pre-launch / Ascent
    PRELAUNCH = "PRELAUNCH"


@dataclass(frozen=True)
class AttitudeSegment:
    """One contiguous segment of constant attitude mode."""

    met_start: timedelta  # Mission Elapsed Time start
    met_end: timedelta    # Mission Elapsed Time end (exclusive)
    mode: AttitudeMode
    description: str


# =============================================================================
# ATTITUDE TIMELINE — Canonical PDF Truth Model (107 verified cells)
# =============================================================================
# Format: (MET_start, MET_end, AttitudeMode, description)
# MET format: "DD/HH:MM" = days/hours:minutes from liftoff
# Boundary types: EXPLICIT_MET (from PDF text) or GRAPHICAL_GRID (from timeline grid)

ATTITUDE_TIMELINE: list[AttitudeSegment] = [
    # Flight Day 01 (FD01) — MET 00/00:00 to 01/00:00
    AttitudeSegment(
        met_start=timedelta(seconds=0),
        met_end=timedelta(hours=1),
        mode=AttitudeMode.PRELAUNCH,
        description="Prelaunch to Ascent: Not applicable prior to orbital insertion",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=1),
        met_end=timedelta(hours=1, minutes=48),
        mode=AttitudeMode.T_ROLL_MNVRS,
        description="Tail-Roll Maneuvers",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=1, minutes=48),
        met_end=timedelta(hours=2),
        mode=AttitudeMode.BURN_ARB,
        description="ARB TIG 0/01:48",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=2),
        met_end=timedelta(hours=3, minutes=24),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=3, minutes=24),
        met_end=timedelta(hours=3, minutes=30),
        mode=AttitudeMode.SEP,
        description="ICPS Spring Sep 0/03:24",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=3, minutes=30),
        met_end=timedelta(hours=5),
        mode=AttitudeMode.POD_ATT,
        description="Proximity Operations Demo",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=5, minutes=2),
        met_end=timedelta(hours=5, minutes=30),
        mode=AttitudeMode.SEP,
        description="ICPS Disposal Burn 0/05:02",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=5, minutes=30),
        met_end=timedelta(hours=8, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=8, minutes=30),
        met_end=timedelta(hours=9),
        mode=AttitudeMode.DFTO_ATTITUDE,
        description="DFTO attitude",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=9),
        met_end=timedelta(hours=10),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=10, minutes=6),
        met_end=timedelta(hours=11),
        mode=AttitudeMode.OPCOMM,
        description="OpComm Intl Act 0/10:06",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=11),
        met_end=timedelta(hours=12, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=12, minutes=30),
        met_end=timedelta(hours=13, minutes=45),
        mode=AttitudeMode.SFM,
        description="Pre-burn setup",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=13, minutes=45),
        met_end=timedelta(hours=14),
        mode=AttitudeMode.BURN_PRB,
        description="Orion PRB 0/13:45",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=14),
        met_end=timedelta(hours=14, minutes=15),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=14, minutes=15),
        met_end=timedelta(hours=15),
        mode=AttitudeMode.OPNAV,
        description="OpNav C/O",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=15),
        met_end=timedelta(hours=15, minutes=30),
        mode=AttitudeMode.SFM,
        description="Pre-burn setup",
    ),
    AttitudeSegment(
        met_start=timedelta(hours=15, minutes=30),
        met_end=timedelta(days=1),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),

    # Flight Day 02 (FD02) — MET 17:00 to 01/17:00
    AttitudeSegment(
        met_start=timedelta(hours=17),
        met_end=timedelta(days=1, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=1, minutes=30),
        met_end=timedelta(days=1, hours=1),
        mode=AttitudeMode.DOCK_CAM,
        description="Dock Cam pointing",
    ),
    AttitudeSegment(
        met_start=timedelta(days=1, hours=1),
        met_end=timedelta(days=1, hours=1, minutes=15),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=1, hours=1, minutes=15),
        met_end=timedelta(days=1, hours=1, minutes=37),
        mode=AttitudeMode.SFM,
        description="Pre-TLI setup",
    ),
    AttitudeSegment(
        met_start=timedelta(days=1, hours=1, minutes=37),
        met_end=timedelta(days=1, hours=2),
        mode=AttitudeMode.BURN_TLI,
        description="Orion TLI 01/01:37",
    ),
    AttitudeSegment(
        met_start=timedelta(days=1, hours=2),
        met_end=timedelta(days=1, hours=8, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=1, hours=8, minutes=30),
        met_end=timedelta(days=1, hours=14),
        mode=AttitudeMode.SURVEY_ATT,
        description="CM/SM Survey 01/12:00",
    ),
    AttitudeSegment(
        met_start=timedelta(days=1, hours=14),
        met_end=timedelta(days=1, hours=17),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),

    # Flight Day 03 (FD03) — MET 01/17:00 to 02/17:00
    AttitudeSegment(
        met_start=timedelta(days=1, hours=17),
        met_end=timedelta(days=1, hours=21),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=1, hours=21),
        met_end=timedelta(days=1, hours=22),
        mode=AttitudeMode.OPNAV,
        description="OpNav pointing",
    ),
    AttitudeSegment(
        met_start=timedelta(days=1, hours=22),
        met_end=timedelta(days=1, hours=22, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=1, hours=22, minutes=30),
        met_end=timedelta(days=1, hours=23, minutes=30),
        mode=AttitudeMode.SFM,
        description="Pre-OTC-1 setup",
    ),
    AttitudeSegment(
        met_start=timedelta(days=1, hours=23, minutes=30),
        met_end=timedelta(days=2, minutes=7),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=2, minutes=7),
        met_end=timedelta(days=2, minutes=30),
        mode=AttitudeMode.BURN_OTC,
        description="OTC-1 02/00:07",
    ),
    AttitudeSegment(
        met_start=timedelta(days=2, minutes=30),
        met_end=timedelta(days=2, hours=5, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=2, hours=5, minutes=30),
        met_end=timedelta(days=2, hours=7),
        mode=AttitudeMode.FTO_ATTITUDE,
        description="FTO attitude (Emergency Comm DFTO, SAW Shadow Test)",
    ),
    AttitudeSegment(
        met_start=timedelta(days=2, hours=7),
        met_end=timedelta(days=2, hours=8, minutes=30),
        mode=AttitudeMode.DOCK_CAM,
        description="Dock Cam pointing",
    ),
    AttitudeSegment(
        met_start=timedelta(days=2, hours=8, minutes=30),
        met_end=timedelta(days=2, hours=10),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=2, hours=10),
        met_end=timedelta(days=2, hours=11),
        mode=AttitudeMode.DFTO_ATTITUDE,
        description="DFTO attitude",
    ),
    AttitudeSegment(
        met_start=timedelta(days=2, hours=11),
        met_end=timedelta(days=2, hours=13, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=2, hours=13, minutes=30),
        met_end=timedelta(days=2, hours=14, minutes=30),
        mode=AttitudeMode.DFTO_ATTITUDE,
        description="DFTO attitude",
    ),
    AttitudeSegment(
        met_start=timedelta(days=2, hours=14, minutes=30),
        met_end=timedelta(days=2, hours=17),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),

    # Flight Day 04 (FD04) — MET 02/17:00 to 03/17:00
    AttitudeSegment(
        met_start=timedelta(days=2, hours=17),
        met_end=timedelta(days=2, hours=21),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=2, hours=21),
        met_end=timedelta(days=2, hours=22),
        mode=AttitudeMode.OPNAV,
        description="OpNav pointing",
    ),
    AttitudeSegment(
        met_start=timedelta(days=2, hours=22),
        met_end=timedelta(days=2, hours=22, minutes=45),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=2, hours=22, minutes=45),
        met_end=timedelta(days=2, hours=23, minutes=30),
        mode=AttitudeMode.SFM,
        description="Pre-OTC-2 setup",
    ),
    AttitudeSegment(
        met_start=timedelta(days=2, hours=23, minutes=30),
        met_end=timedelta(days=3, minutes=12),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=3, minutes=12),
        met_end=timedelta(days=3, minutes=30),
        mode=AttitudeMode.BURN_OTC,
        description="OTC-2 03/00:12",
    ),
    AttitudeSegment(
        met_start=timedelta(days=3, minutes=30),
        met_end=timedelta(days=3, hours=2),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=3, hours=2),
        met_end=timedelta(days=3, hours=4),
        mode=AttitudeMode.DFTO_ATTITUDE,
        description="DFTO attitude (Acoustic DFTO, OpComm CFDP Demo)",
    ),
    AttitudeSegment(
        met_start=timedelta(days=3, hours=4),
        met_end=timedelta(days=3, hours=6, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=3, hours=6, minutes=30),
        met_end=timedelta(days=3, hours=7, minutes=30),
        mode=AttitudeMode.FTO_ATTITUDE,
        description="FTO attitude (Internal Demo FTOs)",
    ),
    AttitudeSegment(
        met_start=timedelta(days=3, hours=7, minutes=30),
        met_end=timedelta(days=3, hours=8, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=3, hours=8, minutes=30),
        met_end=timedelta(days=3, hours=9, minutes=30),
        mode=AttitudeMode.DFTO_ATTITUDE,
        description="DFTO attitude (Dock Cam Stray Light, Misalignment)",
    ),
    AttitudeSegment(
        met_start=timedelta(days=3, hours=9, minutes=30),
        met_end=timedelta(days=3, hours=13),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=3, hours=13),
        met_end=timedelta(days=3, hours=15),
        mode=AttitudeMode.DFTO_ATTITUDE,
        description="DFTO attitude (Dock Cam Misalignment)",
    ),
    AttitudeSegment(
        met_start=timedelta(days=3, hours=15),
        met_end=timedelta(days=3, hours=17),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),

    # Flight Day 05 (FD05) — MET 03/17:00 to 04/17:00
    AttitudeSegment(
        met_start=timedelta(days=3, hours=17),
        met_end=timedelta(days=3, hours=21),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=3, hours=21),
        met_end=timedelta(days=3, hours=22),
        mode=AttitudeMode.OPNAV,
        description="OpNav pointing",
    ),
    AttitudeSegment(
        met_start=timedelta(days=3, hours=22),
        met_end=timedelta(days=3, hours=23),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=3, hours=23),
        met_end=timedelta(days=4, hours=4, minutes=30),
        mode=AttitudeMode.SFM,
        description="Pre-OTC-3 setup",
    ),
    AttitudeSegment(
        met_start=timedelta(days=4, hours=4, minutes=30),
        met_end=timedelta(days=4, hours=5, minutes=23),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=4, hours=5, minutes=23),
        met_end=timedelta(days=4, hours=6),
        mode=AttitudeMode.BURN_OTC,
        description="OTC-3 04/05:23",
    ),
    AttitudeSegment(
        met_start=timedelta(days=4, hours=6),
        met_end=timedelta(days=4, hours=8, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=4, hours=8, minutes=30),
        met_end=timedelta(days=4, hours=10, minutes=30),
        mode=AttitudeMode.DFTO_ATTITUDE,
        description="DFTO attitude (OpComm ANU Demo, Dock Cam Misalignment)",
    ),
    AttitudeSegment(
        met_start=timedelta(days=4, hours=10, minutes=30),
        met_end=timedelta(days=4, hours=17),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),

    # Flight Day 06 (FD06) — MET 04/17:00 to 05/17:00
    AttitudeSegment(
        met_start=timedelta(days=4, hours=17),
        met_end=timedelta(days=4, hours=23),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=4, hours=23),
        met_end=timedelta(days=5, hours=3),
        mode=AttitudeMode.OBSV,
        description="Close Approach 05/01:23",
    ),
    AttitudeSegment(
        met_start=timedelta(days=5, hours=3),
        met_end=timedelta(days=5, hours=4),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=5, hours=4),
        met_end=timedelta(days=5, hours=8, minutes=30),
        mode=AttitudeMode.SURVEY_ATT,
        description="CM/SM Survey 05/12:45",
    ),
    AttitudeSegment(
        met_start=timedelta(days=5, hours=8, minutes=30),
        met_end=timedelta(days=5, hours=17),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),

    # Flight Day 07 (FD07) — MET 05/17:00 to 06/17:00
    AttitudeSegment(
        met_start=timedelta(days=5, hours=17),
        met_end=timedelta(days=5, hours=21),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=5, hours=21),
        met_end=timedelta(days=5, hours=22),
        mode=AttitudeMode.OPNAV,
        description="OpNav pointing",
    ),
    AttitudeSegment(
        met_start=timedelta(days=5, hours=22),
        met_end=timedelta(days=6),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=6),
        met_end=timedelta(days=6, hours=4),
        mode=AttitudeMode.SFM,
        description="Pre-RTC-1 setup",
    ),
    AttitudeSegment(
        met_start=timedelta(days=6, hours=4),
        met_end=timedelta(days=6, hours=4, minutes=23),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=6, hours=4, minutes=23),
        met_end=timedelta(days=6, hours=5),
        mode=AttitudeMode.BURN_RTC,
        description="RTC-1 06/04:23",
    ),
    AttitudeSegment(
        met_start=timedelta(days=6, hours=5),
        met_end=timedelta(days=6, hours=6),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=6, hours=6),
        met_end=timedelta(days=6, hours=7),
        mode=AttitudeMode.FTO_ATTITUDE,
        description="FTO attitude",
    ),
    AttitudeSegment(
        met_start=timedelta(days=6, hours=7),
        met_end=timedelta(days=6, hours=8),
        mode=AttitudeMode.FTO_WW_VIEW,
        description="FTO Window View",
    ),
    AttitudeSegment(
        met_start=timedelta(days=6, hours=8),
        met_end=timedelta(days=6, hours=10, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=6, hours=10, minutes=30),
        met_end=timedelta(days=6, hours=17),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),

    # Flight Day 08 (FD08) — MET 06/17:00 to 07/17:00
    AttitudeSegment(
        met_start=timedelta(days=6, hours=17),
        met_end=timedelta(days=7, hours=4, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=7, hours=4, minutes=30),
        met_end=timedelta(days=7, hours=6, minutes=30),
        mode=AttitudeMode.DFTO_ATTITUDE,
        description="DFTO attitude (Urine Venting, No PCD DFTOs)",
    ),
    AttitudeSegment(
        met_start=timedelta(days=7, hours=6, minutes=30),
        met_end=timedelta(days=7, hours=8, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=7, hours=8, minutes=30),
        met_end=timedelta(days=7, hours=10, minutes=30),
        mode=AttitudeMode.DFTO_ATTITUDE,
        description="DFTO attitude (COGN Test, Urine/Toilet Demo, Radiation Shelter, Manual Piloting)",
    ),
    AttitudeSegment(
        met_start=timedelta(days=7, hours=10, minutes=30),
        met_end=timedelta(days=7, hours=12, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=7, hours=12, minutes=30),
        met_end=timedelta(days=7, hours=14),
        mode=AttitudeMode.DFTO_ATTITUDE,
        description="DFTO attitude",
    ),
    AttitudeSegment(
        met_start=timedelta(days=7, hours=14),
        met_end=timedelta(days=7, hours=15, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=7, hours=15, minutes=30),
        met_end=timedelta(days=7, hours=17),
        mode=AttitudeMode.BIAS_NEG_XSI_MITIGATE_X,
        description="Bias -XSI Mitigate X",
    ),

    # Flight Day 09 (FD09) — MET 07/17:00 to 08/17:00
    AttitudeSegment(
        met_start=timedelta(days=7, hours=17),
        met_end=timedelta(days=7, hours=20),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=7, hours=20),
        met_end=timedelta(days=7, hours=22),
        mode=AttitudeMode.DFTO_ATTITUDE,
        description="DFTO attitude",
    ),
    AttitudeSegment(
        met_start=timedelta(days=7, hours=22),
        met_end=timedelta(days=7, hours=23, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI_MITIGATE_X,
        description="Bias -XSI Mitigate X",
    ),
    AttitudeSegment(
        met_start=timedelta(days=7, hours=23, minutes=30),
        met_end=timedelta(days=8, hours=1),
        mode=AttitudeMode.OPNAV,
        description="OpNav pointing",
    ),
    AttitudeSegment(
        met_start=timedelta(days=8, hours=1),
        met_end=timedelta(days=8, hours=2, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=8, hours=2, minutes=30),
        met_end=timedelta(days=8, hours=4),
        mode=AttitudeMode.SFM,
        description="Pre-RTC-2 setup",
    ),
    AttitudeSegment(
        met_start=timedelta(days=8, hours=4),
        met_end=timedelta(days=8, hours=4, minutes=33),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=8, hours=4, minutes=33),
        met_end=timedelta(days=8, hours=5),
        mode=AttitudeMode.BURN_RTC,
        description="RTC-2 08/04:33",
    ),
    AttitudeSegment(
        met_start=timedelta(days=8, hours=5),
        met_end=timedelta(days=8, hours=17),
        mode=AttitudeMode.BIAS_NEG_XSI_MITIGATE_X,
        description="Bias -XSI Mitigate X",
    ),

    # Flight Day 10 (FD10) — MET 08/17:00 to 09/04:00+
    AttitudeSegment(
        met_start=timedelta(days=8, hours=17),
        met_end=timedelta(days=8, hours=19),
        mode=AttitudeMode.OPNAV,
        description="OpNav pointing",
    ),
    AttitudeSegment(
        met_start=timedelta(days=8, hours=19),
        met_end=timedelta(days=8, hours=19, minutes=45),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=8, hours=19, minutes=45),
        met_end=timedelta(days=8, hours=20, minutes=15),
        mode=AttitudeMode.SFM,
        description="Pre-RTC-3 setup",
    ),
    AttitudeSegment(
        met_start=timedelta(days=8, hours=20, minutes=15),
        met_end=timedelta(days=8, hours=20, minutes=33),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=8, hours=20, minutes=33),
        met_end=timedelta(days=8, hours=21),
        mode=AttitudeMode.BURN_RTC,
        description="RTC-3 08/20:33",
    ),
    AttitudeSegment(
        met_start=timedelta(days=8, hours=21),
        met_end=timedelta(days=8, hours=23, minutes=30),
        mode=AttitudeMode.BIAS_NEG_XSI_MITIGATE_X,
        description="Bias -XSI Mitigate X",
    ),
    AttitudeSegment(
        met_start=timedelta(days=8, hours=23, minutes=30),
        met_end=timedelta(days=9, minutes=30),
        mode=AttitudeMode.SFM,
        description="Pre-entry setup",
    ),
    AttitudeSegment(
        met_start=timedelta(days=9, minutes=30),
        met_end=timedelta(days=9, hours=1, minutes=13),
        mode=AttitudeMode.BIAS_NEG_XSI,
        description="Bias -XSI",
    ),
    AttitudeSegment(
        met_start=timedelta(days=9, hours=1, minutes=13),
        met_end=timedelta(days=9, hours=1, minutes=33),
        mode=AttitudeMode.SEP,
        description="CM/SM Sep 09/01:13",
    ),
    AttitudeSegment(
        met_start=timedelta(days=9, hours=1, minutes=33),
        met_end=timedelta(days=9, hours=1, minutes=46),
        mode=AttitudeMode.EDL,
        description="Entry Interface 09/01:33 to Splashdown 09/01:46",
    ),
    AttitudeSegment(
        met_start=timedelta(days=9, hours=1, minutes=46),
        met_end=timedelta(days=9, hours=2),  # approximate recovery start
        mode=AttitudeMode.RECOVERY,
        description="Splashdown / Recovery",
    ),
]


def parse_met(met_str: str) -> timedelta:
    """Parse Mission Elapsed Time string (DD/HH:MM or HH:MM) to timedelta."""
    parts = met_str.split("/")
    if len(parts) == 2:
        days = int(parts[0])
        time_part = parts[1]
    else:
        days = 0
        time_part = parts[0]

    if ":" in time_part:
        h, m = map(int, time_part.split(":"))
    else:
        h = int(time_part)
        m = 0

    return timedelta(days=days, hours=h, minutes=m)


def format_met(td: timedelta) -> str:
    """Format timedelta as MET string DD/HH:MM."""
    total_minutes = int(td.total_seconds() / 60)
    days = total_minutes // (24 * 60)
    rem = total_minutes % (24 * 60)
    hours = rem // 60
    minutes = rem % 60
    return f"{days:02d}/{hours:02d}:{minutes:02d}"


def get_attitude_mode(met: timedelta) -> AttitudeSegment | None:
    """Get the attitude segment active at the given MET.

    Returns None if MET is before liftoff or after the last defined segment.
    """
    for segment in ATTITUDE_TIMELINE:
        if segment.met_start <= met < segment.met_end:
            return segment
    return None


def get_attitude_mode_at_met_str(met_str: str) -> AttitudeSegment | None:
    """Get attitude segment by MET string (e.g., '02/05:30')."""
    return get_attitude_mode(parse_met(met_str))


def get_all_segments_for_mode(mode: AttitudeMode) -> list[AttitudeSegment]:
    """Get all timeline segments for a specific attitude mode."""
    return [s for s in ATTITUDE_TIMELINE if s.mode == mode]


def get_total_duration_by_mode() -> dict[AttitudeMode, timedelta]:
    """Get total duration spent in each attitude mode."""
    result: dict[AttitudeMode, timedelta] = {}
    for segment in ATTITUDE_TIMELINE:
        duration = segment.met_end - segment.met_start
        result[segment.mode] = result.get(segment.mode, timedelta(0)) + duration
    return result


# =============================================================================
# ATTITUDE MODE → QUATERNION / EULER MAPPING (PLACEHOLDER)
# =============================================================================
# These mappings need to be filled in with actual Orion attitude definitions.
# The timeline gives MODE NAMES; the state engine must resolve them to
# quaternions in the EME2000/J2000 frame.

ATTITUDE_MODE_DEFINITIONS: dict[AttitudeMode, dict] = {
    AttitudeMode.BIAS_NEG_XSI: {
        "description": "Default coast attitude. -X body axis aligned with Sun-spacecraft vector "
                       "(solar arrays sun-pointing). Y/Z axes per mission design.",
        "frame": "EME2000",
        "notes": "Dominant mode (~55% of mission). Solar incidence ~0 deg on +Z arrays.",
    },
    AttitudeMode.BIAS_NEG_XSI_MITIGATE_X: {
        "description": "Modified Bias -XSI to manage X-axis thermal loads. "
                       "Small offset from pure -XSI to reduce shadow-face cooling.",
        "frame": "EME2000",
        "notes": "Used FD08-FD10 for thermal mitigation.",
    },
    AttitudeMode.T_ROLL_MNVRS: {
        "description": "Tail-roll maneuvers for thermal conditioning during early mission.",
        "frame": "LVLH",
        "notes": "FD01 MET 00/01:00-00/01:48. Roll about velocity vector.",
    },
    AttitudeMode.POD_ATT: {
        "description": "Proximity Operations Demo attitude. Specific relative orientation "
                       "for proximity operations demonstration with ICPS.",
        "frame": "LVLH",
        "notes": "FD01 MET 00/03:30-00/05:00.",
    },
    AttitudeMode.BURN_TLI: {
        "description": "Trans-Lunar Injection burn attitude. Thrust vector aligned with "
                       "required delta-V. Solar arrays feathered.",
        "frame": "EME2000",
        "notes": "FD02 MET 01/01:37-01/02:00. ~23 min burn.",
    },
    AttitudeMode.BURN_PRB: {
        "description": "Perigee Raise Burn. Thrust-vector-aligned.",
        "frame": "EME2000",
        "notes": "FD01 MET 00/13:45-00/14:00.",
    },
    AttitudeMode.BURN_OTC: {
        "description": "Outbound Trajectory Correction. Thrust-vector-aligned (OTC-1,2,3).",
        "frame": "EME2000",
        "notes": "OTC-1: 02/00:07-02/00:30, OTC-2: 03/00:12-03/00:30, OTC-3: 04/05:23-04/06:00",
    },
    AttitudeMode.BURN_RTC: {
        "description": "Return Trajectory Correction. Thrust-vector-aligned (RTC-1,2,3).",
        "frame": "EME2000",
        "notes": "RTC-1: 06/04:23-06/05:00, RTC-2: 08/04:33-08/05:00, RTC-3: 08/20:33-08/21:00",
    },
    AttitudeMode.BURN_ARB: {
        "description": "Ascent Abort / ARB burn attitude. Thrust-vector-aligned.",
        "frame": "EME2000",
        "notes": "FD01 MET 00/01:48-00/02:00.",
    },
    AttitudeMode.SFM: {
        "description": "Pre-burn setup / Final Maneuver. Vehicle reorients for upcoming burn.",
        "frame": "EME2000",
        "notes": "Precedes each major burn. Solar arrays may be repositioned.",
    },
    AttitudeMode.SEP: {
        "description": "CM/SM Separation attitude. Service Module jettison, CM reorients for entry.",
        "frame": "EME2000",
        "notes": "FD10 MET 09/01:13-09/01:33. ICPS Spring Sep at 00/03:24, ICPS Disposal at 00/05:02.",
    },
    AttitudeMode.SURVEY_ATT: {
        "description": "CM/SM Survey attitude. Vehicle oriented for external camera inspection.",
        "frame": "EME2000",
        "notes": "FD02 01/08:30-01/14:00, FD06 05/04:00-05/08:30. Slow roll for 360 deg coverage.",
    },
    AttitudeMode.DOCK_CAM: {
        "description": "Docking camera pointing. Specific orientation for dock cam operations.",
        "frame": "LVLH",
        "notes": "FD02 01/00:30-01/01:00, FD03 02/07:00-02/08:30. Docking camera boresight aligned to target.",
    },
    AttitudeMode.OPNAV: {
        "description": "Optical Navigation pointing. Star tracker / OpNav camera "
                       "oriented to celestial targets for navigation updates.",
        "frame": "EME2000",
        "notes": "Multiple short segments throughout mission.",
    },
    AttitudeMode.OPCOMM: {
        "description": "Optical Communication activation attitude.",
        "frame": "EME2000",
        "notes": "FD01 MET 00/10:06-00/11:00.",
    },
    AttitudeMode.OBSV: {
        "description": "Lunar observation attitude. Windows/optics pointed at lunar surface "
                       "during close approach and max Earth distance.",
        "frame": "LVLH",
        "notes": "FD06 MET 04/23:00-05/03:00. Lunar Flyby observations.",
    },
    AttitudeMode.FTO_ATTITUDE: {
        "description": "Flight Test Objective specific attitude. Varies by FTO. "
                       "Default placeholder — actual attitude depends on specific FTO.",
        "frame": "VARIES",
        "notes": "Generic placeholder. Actual FTO attitudes in FTO procedures.",
    },
    AttitudeMode.FTO_WW_VIEW: {
        "description": "FTO Window View attitude. Crew window viewing orientation.",
        "frame": "LVLH",
        "notes": "FD07 MET 06/07:00-06/08:00.",
    },
    AttitudeMode.DFTO_ATTITUDE: {
        "description": "Detailed Flight Test Objective specific attitude. Varies by DFTO.",
        "frame": "VARIES",
        "notes": "Generic placeholder. Actual DFTO attitudes in DFTO procedures.",
    },
    AttitudeMode.EDL: {
        "description": "Entry Interface through descent. Heat shield forward (-X axis "
                       "aligned with velocity vector). Guided entry with bank angle control.",
        "frame": "EME2000",
        "notes": "FD10 MET 09/01:33-09/01:46. EI at 09/01:33, Splashdown at 09/01:46. ~13 min.",
    },
    AttitudeMode.RECOVERY: {
        "description": "Post-splashdown / Recovery attitude. CM upright in water, awaiting recovery.",
        "frame": "EME2000",
        "notes": "FD10 MET 09/01:46 onwards. Recovery operations begin.",
    },
    AttitudeMode.ENTRY_ATTITUDE: {
        "description": "Entry, Descent, Landing attitude (legacy combined). Heat shield forward "
                       "(-X axis aligned with velocity vector). CM/SM separation attitude first.",
        "frame": "EME2000",
        "notes": "FD10 MET 09/01:13-09/01:46. Use SEP + EDL + RECOVERY for granular phases.",
    },
    AttitudeMode.PRELAUNCH: {
        "description": "Pre-launch / ascent phase. Attitude not controlled by Orion GNC.",
        "frame": "N/A",
        "notes": "MET < 0. Not applicable for on-orbit simulation.",
    },
}


def get_mode_definition(mode: AttitudeMode) -> dict:
    """Get the definition/metadata for an attitude mode."""
    return ATTITUDE_MODE_DEFINITIONS.get(mode, {"description": "Unknown mode", "frame": "UNKNOWN"})


# =============================================================================
# MAIN ENTRY POINT FOR STATE ENGINE
# =============================================================================

def resolve_attitude(met: timedelta) -> tuple[AttitudeMode, dict]:
    """Resolve MET to attitude mode and its definition.

    Returns:
        (AttitudeMode, definition_dict)

    The definition_dict contains frame, description, notes for the state engine
    to compute the actual quaternion/Euler angles.
    """
    segment = get_attitude_mode(met)
    if segment is None:
        # Before liftoff or after defined timeline
        if met < timedelta(0):
            return AttitudeMode.PRELAUNCH, get_mode_definition(AttitudeMode.PRELAUNCH)
        # After timeline ends — hold last known (Recovery)
        return AttitudeMode.RECOVERY, get_mode_definition(AttitudeMode.RECOVERY)

    return segment.mode, get_mode_definition(segment.mode)


def get_solar_incidence_angle_estimate(met: timedelta) -> float:
    """Estimate solar incidence angle for the given MET.

    This is a rough estimate based on attitude mode. The state engine should
    compute the true angle from the resolved quaternion and Sun vector.

    Returns:
        Estimated solar incidence angle in degrees (0 = arrays face Sun).
    """
    mode, _ = resolve_attitude(met)

    # Rough estimates based on mode semantics
    if mode in (AttitudeMode.BIAS_NEG_XSI, AttitudeMode.BIAS_NEG_XSI_MITIGATE_X):
        return 0.0  # Arrays sun-pointing by design
    if mode in (AttitudeMode.BURN_TLI, AttitudeMode.BURN_PRB,
                AttitudeMode.BURN_OTC, AttitudeMode.BURN_RTC, AttitudeMode.BURN_ARB):
        return 90.0  # Arrays feathered during burns
    if mode in (AttitudeMode.SEP, AttitudeMode.EDL, AttitudeMode.RECOVERY, AttitudeMode.ENTRY_ATTITUDE):
        return 180.0  # Heat shield forward, arrays edge-on/stowed
    if mode in (AttitudeMode.POD_ATT, AttitudeMode.SURVEY_ATT,
                AttitudeMode.DOCK_CAM, AttitudeMode.OPNAV,
                AttitudeMode.OPCOMM, AttitudeMode.OBSV):
        return 45.0  # Rough estimate for off-nominal attitudes
    if mode in (AttitudeMode.FTO_ATTITUDE, AttitudeMode.FTO_WW_VIEW,
                AttitudeMode.DFTO_ATTITUDE):
        return 60.0  # Unknown FTO/DFTO attitudes — conservative estimate
    if mode == AttitudeMode.T_ROLL_MNVRS:
        return 30.0  # Rolling — average
    if mode == AttitudeMode.SFM:
        return 60.0  # Pre-burn transition

    return 0.0  # Default to sun-pointing


def get_solar_array_gimbal_estimate(met: timedelta) -> float:
    """Estimate solar array gimbal offset from optimal sun-tracking.

    Returns:
        Estimated gimbal offset in degrees (0 = fully tracking).
    """
    mode, _ = resolve_attitude(met)

    if mode in (AttitudeMode.BIAS_NEG_XSI, AttitudeMode.BIAS_NEG_XSI_MITIGATE_X):
        return 0.0  # Arrays track Sun in Bias -XSI
    if mode in (AttitudeMode.BURN_TLI, AttitudeMode.BURN_PRB,
                AttitudeMode.BURN_OTC, AttitudeMode.BURN_RTC, AttitudeMode.BURN_ARB):
        return 90.0  # Arrays feathered (edge-on to Sun) during burns
    if mode in (AttitudeMode.SEP, AttitudeMode.EDL, AttitudeMode.RECOVERY, AttitudeMode.ENTRY_ATTITUDE):
        return 90.0  # Arrays stowed/feathered
    if mode == AttitudeMode.T_ROLL_MNVRS:
        return 15.0  # Small offset during roll maneuvers
    if mode == AttitudeMode.SFM:
        return 45.0  # Transition

    return 15.0  # Conservative estimate for off-nominal attitudes


if __name__ == "__main__":
    # Quick sanity check
    print("Artemis II Planned Attitude Profile Summary")
    print("=" * 60)

    durations = get_total_duration_by_mode()
    total = sum(durations.values(), timedelta(0))

    for mode, dur in sorted(durations.items(), key=lambda x: x[1], reverse=True):
        pct = (dur / total * 100) if total > timedelta(0) else 0
        print(f"  {mode.value:30s}  {dur}  ({pct:.1f}%)")

    print(f"\nTotal timeline: {total}")
    print(f"Total segments: {len(ATTITUDE_TIMELINE)}")

    # Test resolution at key points
    test_mets = [
        timedelta(seconds=0),
        timedelta(hours=1, minutes=30),
        timedelta(hours=1, minutes=50),
        timedelta(hours=3, minutes=25),
        timedelta(hours=14, minutes=20),
        timedelta(days=1, hours=1, minutes=40),
        timedelta(days=2, minutes=15),
        timedelta(days=4, hours=23, minutes=30),
        timedelta(days=6, hours=4, minutes=30),
        timedelta(days=9, hours=1, minutes=20),
        timedelta(days=9, hours=1, minutes=40),
    ]

    print("\nSample MET resolutions:")
    for met in test_mets:
        mode, _ = resolve_attitude(met)
        inc = get_solar_incidence_angle_estimate(met)
        gimbal = get_solar_array_gimbal_estimate(met)
        print(f"  MET {format_met(met):>8s} -> {mode.value:25s}  inc={inc:.0f}deg gimbal={gimbal:.0f}deg")