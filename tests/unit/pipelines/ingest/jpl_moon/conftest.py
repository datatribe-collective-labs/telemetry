"""Fixtures for unit tests of pipelines.ingest.jpl_moon."""

import pytest

# Shaped like a plain-text Horizons VECTORS response for the Moon (301), Earth-centred,
# OUT_UNITS=KM-S, TIME_TYPE=UT, no CSV_FORMAT. Values are illustrative.
VECTORS_RESULT = """\
*******************************************************************************
Target body name: Moon (301)                      {source: DE441}
Center body name: Earth (399)                     {source: DE441}
*******************************************************************************
$$SOE
2461132.395833333 = A.D. 2026-Apr-01 21:30:00.0000 UTC
 X =-3.000000000000000E+05 Y = 2.000000000000000E+05 Z = 1.000000000000000E+05
 VX=-5.000000000000000E-01 VY=-7.000000000000000E-01 VZ=-3.000000000000000E-01
 LT= 1.247000000000000E+00 RG= 3.741657386773941E+05 RR= 1.000000000000000E-02
2461132.437500000 = A.D. 2026-Apr-01 22:30:00.0000 UTC
 X =-3.018000000000000E+05 Y = 1.974800000000000E+05 Z = 9.892000000000000E+04
 VX=-5.000000000000000E-01 VY=-7.000000000000000E-01 VZ=-3.000000000000000E-01
 LT= 1.247100000000000E+00 RG= 3.741700000000000E+05 RR= 1.000000000000000E-02
$$EOE
*******************************************************************************
"""


@pytest.fixture
def vectors_result():
    return VECTORS_RESULT
