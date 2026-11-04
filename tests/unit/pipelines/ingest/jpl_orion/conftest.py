"""Fixtures for unit tests of pipelines.ingest.jpl_orion."""

import pytest

# Shaped like a Horizons VECTORS response for -1024 (VEC_TABLE=3, CSV_FORMAT=YES,
# OUT_UNITS=KM-S, TIME_TYPE=UT). Like the real API, the CSV header sits above $$SOE.
# Values are illustrative, not copied from a real response.
VECTORS_RESULT = """\
*******************************************************************************
Target body name: Artemis II (spacecraft) (-1024)
Center body name: Earth (399)                     {source: DE441}
Reference frame : ICRF
*******************************************************************************
            JDUT ,            Calendar Date (UT ),                    X,                      Y,                      Z,                     VX,                     VY,                     VZ,                     LT,                     RG,                     RR,
**************************************************************************************************************************************************************************
$$SOE
2461132.583333333, A.D. 2026-Apr-02 02:00:00.0000,  1.000000000000000E+04,  2.000000000000000E+04,  3.000000000000000E+03,  1.000000000000000E+00,  2.000000000000000E+00,  2.000000000000000E+00,  7.495719986630610E-02,  2.247220505424423E+04,  2.500000000000000E+00,
2461132.625000000, A.D. 2026-Apr-02 03:00:00.0000,  1.360000000000000E+04,  2.720000000000000E+04,  1.020000000000000E+04,  9.000000000000000E-01,  1.800000000000000E+00,  1.900000000000000E+00,  1.054000000000000E-01,  3.159000000000000E+04,  2.300000000000000E+00,
$$EOE
*******************************************************************************
"""


@pytest.fixture
def vectors_result():
    return VECTORS_RESULT
