"""Fixtures for unit tests of pipelines.ingest.jpl_orion."""

import pytest

# Shaped like a plain-text Horizons VECTORS response for -1024 (VEC_TABLE=3,
# OUT_UNITS=KM-S, TIME_TYPE=UT, no CSV_FORMAT). Values are illustrative, not copied
# from a real response.
VECTORS_RESULT = """\
*******************************************************************************
Target body name: Artemis II (spacecraft) (-1024) {source: Artemis_II_merged}
Center body name: Earth (399)                     {source: DE441}
Output format   : 3 (position, velocity, LT, range, range-rate)
Reference frame : ICRF
*******************************************************************************
JDUT
   X     Y     Z
   VX    VY    VZ
   LT    RG    RR
*******************************************************************************
$$SOE
2461132.583333333 = A.D. 2026-Apr-02 02:00:00.0000 UTC
 X = 1.000000000000000E+04 Y = 2.000000000000000E+04 Z = 3.000000000000000E+03
 VX= 1.000000000000000E+00 VY= 2.000000000000000E+00 VZ= 2.000000000000000E+00
 LT= 7.495719986630610E-02 RG= 2.247220505424423E+04 RR= 2.500000000000000E+00
2461132.625000000 = A.D. 2026-Apr-02 03:00:00.0000 UTC
 X = 1.360000000000000E+04 Y = 2.720000000000000E+04 Z = 1.020000000000000E+04
 VX= 9.000000000000000E-01 VY= 1.800000000000000E+00 VZ= 1.900000000000000E+00
 LT= 1.054000000000000E-01 RG= 3.159000000000000E+04 RR= 2.300000000000000E+00
$$EOE
*******************************************************************************
"""

# What Horizons returned for CSV_FORMAT=YES VECTORS tables in Nov 2026 (#57): the two
# time columns only, no X..RR.
DATES_ONLY_CSV_RESULT = """\
            JDUT ,            Calendar Date (UT ),
$$SOE
2461135.500000000, A.D. 2026-Apr-05 00:00:00.0000,
$$EOE
"""


@pytest.fixture
def vectors_result():
    return VECTORS_RESULT


@pytest.fixture
def dates_only_csv_result():
    return DATES_ONLY_CSV_RESULT
