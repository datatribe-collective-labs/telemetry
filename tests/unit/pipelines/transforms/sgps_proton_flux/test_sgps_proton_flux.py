"""Unit tests for pipelines.transforms.sgps_proton_flux.

Tests cover the physics transform for deriving ≥10 MeV proton flux from
GOES SGPS differential channels. HTTP and database connections are mocked;
these tests do not require external services.
"""

from math import isfinite

import pytest
from pipelines.transforms.sgps_proton_flux import (
    CHANNEL_INDEX_TO_NAME,
    DIFFERENTIAL_PER_KEV,
    DIFFERENTIAL_PER_MEV,
    PFU,
    SgpsChannel,
    SgpsDerivationError,
    SgpsGe10Result,
    channels_from_table_rows,
    convert_differential_to_mev,
    derive_ge10_pfu,
)


class TestConvertDifferentialToMev:
    """Tests for convert_differential_to_mev function."""

    def test_per_kev_to_per_mev_multiply_by_1000(self):
        result = convert_differential_to_mev(1.5, DIFFERENTIAL_PER_KEV)
        assert result == 1500.0

    def test_per_mev_unchanged(self):
        result = convert_differential_to_mev(2.5, DIFFERENTIAL_PER_MEV)
        assert result == 2.5

    def test_zero_allowed(self):
        result = convert_differential_to_mev(0.0, DIFFERENTIAL_PER_KEV)
        assert result == 0.0

    def test_negative_raises(self):
        with pytest.raises(SgpsDerivationError, match="cannot be negative"):
            convert_differential_to_mev(-1.0, DIFFERENTIAL_PER_KEV)

    def test_nan_raises(self):
        with pytest.raises(SgpsDerivationError, match="must be finite"):
            convert_differential_to_mev(float("nan"), DIFFERENTIAL_PER_KEV)

    def test_inf_raises(self):
        with pytest.raises(SgpsDerivationError, match="must be finite"):
            convert_differential_to_mev(float("inf"), DIFFERENTIAL_PER_KEV)

    def test_unknown_units_raises(self):
        with pytest.raises(SgpsDerivationError, match="unsupported differential-flux units"):
            convert_differential_to_mev(1.0, "unknown/units")


class TestChannelsFromTableRows:
    """Tests for channels_from_table_rows adapter function."""

    def _make_row(self, idx: int, flux: float, lower: float, upper: float,
                  valid: int = 10, dqf: int = 0) -> dict:
        return {
            "channel_index": idx,
            "flux": flux,
            "energy_lower_mev": lower,
            "energy_upper_mev": upper,
            "valid_sample_count": valid,
            "dqf_sum": dqf,
        }

    def test_basic_conversion_per_kev(self):
        rows = [
            self._make_row(0, 1.0, 1.0, 5.0),   # P1
            self._make_row(1, 2.0, 5.0, 10.0),  # P2
            self._make_row(13, 100.0, 500.0, 0.0),  # >500 MeV integral
        ]
        channels, gt500 = channels_from_table_rows(rows, differential_units=DIFFERENTIAL_PER_KEV)

        assert gt500 == 100.0
        assert len(channels) == 2
        assert channels[0].name == "P1"
        assert channels[0].flux == 1000.0  # 1.0 * 1000
        assert channels[1].name == "P2"
        assert channels[1].flux == 2000.0  # 2.0 * 1000

    def test_per_mev_no_conversion(self):
        rows = [
            self._make_row(0, 1.0, 1.0, 5.0),
            self._make_row(13, 100.0, 500.0, 0.0),
        ]
        channels, _gt500 = channels_from_table_rows(rows, differential_units=DIFFERENTIAL_PER_MEV)

        assert channels[0].flux == 1.0  # unchanged

    def test_quality_mask_excludes_invalid_valid_count(self):
        rows = [
            self._make_row(0, 1.0, 1.0, 5.0, valid=0),  # excluded
            self._make_row(13, 100.0, 500.0, 0.0),
        ]
        channels, _ = channels_from_table_rows(rows, differential_units=DIFFERENTIAL_PER_KEV, mask_quality=True)
        assert len(channels) == 0

    def test_quality_mask_excludes_nonzero_dqf(self):
        rows = [
            self._make_row(0, 1.0, 1.0, 5.0, dqf=1),  # excluded
            self._make_row(13, 100.0, 500.0, 0.0),
        ]
        channels, _ = channels_from_table_rows(rows, differential_units=DIFFERENTIAL_PER_KEV, mask_quality=True)
        assert len(channels) == 0

    def test_quality_mask_disabled_includes_all(self):
        rows = [
            self._make_row(0, 1.0, 1.0, 5.0, valid=0, dqf=1),
            self._make_row(13, 100.0, 500.0, 0.0),
        ]
        channels, _ = channels_from_table_rows(rows, differential_units=DIFFERENTIAL_PER_KEV, mask_quality=False)
        assert len(channels) == 1

    def test_missing_gt500_raises(self):
        rows = [
            self._make_row(0, 1.0, 1.0, 5.0),
            # no channel_index=13
        ]
        with pytest.raises(SgpsDerivationError, match="missing >500 MeV integral channel"):
            channels_from_table_rows(rows, differential_units=DIFFERENTIAL_PER_KEV)

    def test_unknown_channel_index_raises(self):
        rows = [
            self._make_row(99, 1.0, 1.0, 5.0),  # unknown
            self._make_row(13, 100.0, 500.0, 0.0),
        ]
        with pytest.raises(SgpsDerivationError, match="unknown SGPS channel_index=99"):
            channels_from_table_rows(rows, differential_units=DIFFERENTIAL_PER_KEV)

    def test_missing_flux_raises(self):
        rows = [
            {"channel_index": 0, "energy_lower_mev": 1.0, "energy_upper_mev": 5.0},  # no flux
            self._make_row(13, 100.0, 500.0, 0.0),
        ]
        with pytest.raises(SgpsDerivationError, match="missing flux for channel_index=0"):
            channels_from_table_rows(rows, differential_units=DIFFERENTIAL_PER_KEV)

    def test_invalid_energy_bounds_raises(self):
        rows = [
            self._make_row(0, 1.0, 5.0, 1.0),  # lower > upper
            self._make_row(13, 100.0, 500.0, 0.0),
        ]
        with pytest.raises(SgpsDerivationError, match="energy bounds must satisfy 0 < lower < upper"):
            channels_from_table_rows(rows, differential_units=DIFFERENTIAL_PER_KEV)


class TestDeriveGe10Pfu:
    """Tests for derive_ge10_pfu core physics transform."""

    def _make_channel(self, name: str, lower: float, upper: float, flux: float) -> SgpsChannel:
        return SgpsChannel(name=name, lower_mev=lower, upper_mev=upper, flux=flux)

    def test_basic_derivation_with_gt500(self):
        channels = [
            self._make_channel("P4", 15.0, 40.0, 10.0),
            self._make_channel("P5", 38.0, 82.0, 5.0),
            self._make_channel("P6", 84.0, 200.0, 2.0),
        ]
        gt500 = 1.5

        result = derive_ge10_pfu(channels, gt500)

        assert isinstance(result, SgpsGe10Result)
        assert result.flux_ge10_pfu > 0
        assert isfinite(result.flux_ge10_pfu)
        assert result.method == "power_law_loglog_sgps_v2"
        assert result.status == "provisional"
        assert result.integral_gt500_pfu == 1.5

    def test_requires_at_least_two_positive_channels(self):
        channels = [self._make_channel("P4", 15.0, 40.0, 10.0)]
        gt500 = 1.5

        with pytest.raises(SgpsDerivationError, match="fewer than two positive channels"):
            derive_ge10_pfu(channels, gt500)

    def test_zero_channels_excluded_and_counted(self):
        channels = [
            self._make_channel("P4", 15.0, 40.0, 0.0),  # zero - excluded
            self._make_channel("P5", 38.0, 82.0, 5.0),
            self._make_channel("P6", 84.0, 200.0, 2.0),
        ]
        gt500 = 1.5

        result = derive_ge10_pfu(channels, gt500)

        assert result.zero_channel_count == 1
        assert len(result.fit_channel_names) == 2  # P5, P6 only

    def test_negative_flux_raises(self):
        channels = [
            self._make_channel("P4", 15.0, 40.0, -1.0),
            self._make_channel("P5", 38.0, 82.0, 5.0),
        ]
        gt500 = 1.5

        with pytest.raises(SgpsDerivationError, match="flux cannot be negative"):
            derive_ge10_pfu(channels, gt500)

    def test_nan_flux_raises(self):
        channels = [
            self._make_channel("P4", 15.0, 40.0, float("nan")),
            self._make_channel("P5", 38.0, 82.0, 5.0),
        ]
        gt500 = 1.5

        with pytest.raises(SgpsDerivationError, match="must be finite"):
            derive_ge10_pfu(channels, gt500)

    def test_negative_gt500_raises(self):
        channels = [
            self._make_channel("P4", 15.0, 40.0, 10.0),
            self._make_channel("P5", 38.0, 82.0, 5.0),
        ]
        gt500 = -1.0

        with pytest.raises(SgpsDerivationError, match=">500 MeV integral flux cannot be negative"):
            derive_ge10_pfu(channels, gt500)

    def test_nan_gt500_raises(self):
        channels = [
            self._make_channel("P4", 15.0, 40.0, 10.0),
            self._make_channel("P5", 38.0, 82.0, 5.0),
        ]
        gt500 = float("nan")

        with pytest.raises(SgpsDerivationError, match="must be finite"):
            derive_ge10_pfu(channels, gt500)

    def test_lower_bound_invariant_direct_measured(self):
        """
        Test that derived >= direct measured (bands with lower >= 10 MeV + >500 MeV).

        The transform's direct lower bound includes channels where lower_mev >= 10.0.
        P4 (15-40 MeV) has lower=15 >= 10, so it IS included in the direct calculation.
        """
        channels = [
            self._make_channel("P4", 15.0, 40.0, 10.0),  # lower=15 >= 10, included
            self._make_channel("P5", 38.0, 82.0, 5.0),   # lower=38 >= 10, included
            self._make_channel("P6", 84.0, 200.0, 2.0),  # lower=84 >= 10, included
        ]
        gt500 = 1.5

        result = derive_ge10_pfu(channels, gt500)

        # Direct = gt500 + P4_width * P4_flux + P5_width * P5_flux + P6_width * P6_flux
        direct = gt500 + 10.0 * 25.0 + 5.0 * 44.0 + 2.0 * 116.0

        assert result.direct_lower_bound_pfu == direct
        assert result.flux_ge10_pfu >= direct

    def test_p4_included_in_direct_since_lower_ge_10(self):
        """P4 (15-40 MeV) has lower=15 >= 10, so it IS included in direct lower bound."""
        channels = [
            self._make_channel("P4", 15.0, 40.0, 100.0),  # lower=15 >= 10, included in direct
            self._make_channel("P5", 38.0, 82.0, 1.0),    # lower=38 >= 10, also included
        ]
        gt500 = 0.1

        result = derive_ge10_pfu(channels, gt500)

        # Direct includes both P4 (lower=15 >= 10) and P5 (lower=38 >= 10) + gt500
        # P4 width = 25, P5 width = 44
        direct = gt500 + 100.0 * 25.0 + 1.0 * 44.0

        assert result.direct_lower_bound_pfu == direct
        assert "P4" in result.fit_channel_names  # P4 used in fit
        assert "P5" in result.fit_channel_names
        assert result.flux_ge10_pfu >= direct

    def test_uncertainty_with_three_channels(self):
        channels = [
            self._make_channel("P4", 15.0, 40.0, 10.0),
            self._make_channel("P5", 38.0, 82.0, 5.0),
            self._make_channel("P6", 84.0, 200.0, 2.0),
        ]
        gt500 = 1.5

        result = derive_ge10_pfu(channels, gt500)

        # With 3 fit channels, uncertainty should be computed
        assert result.uncertainty_pfu is not None
        assert result.uncertainty_pfu > 0

    def test_uncertainty_none_with_two_channels(self):
        channels = [
            self._make_channel("P5", 38.0, 82.0, 5.0),
            self._make_channel("P6", 84.0, 200.0, 2.0),
        ]
        gt500 = 1.5

        result = derive_ge10_pfu(channels, gt500)

        # With only 2 fit channels, uncertainty is None
        assert result.uncertainty_pfu is None

    def test_channels_below_5_mev_excluded_from_fit(self):
        """Channels entirely below 5 MeV should not be in fit."""
        channels = [
            self._make_channel("P1", 1.0, 5.0, 100.0),  # entirely <5 MeV
            self._make_channel("P4", 15.0, 40.0, 10.0),
            self._make_channel("P5", 38.0, 82.0, 5.0),
        ]
        gt500 = 1.5

        result = derive_ge10_pfu(channels, gt500)

        assert "P1" not in result.fit_channel_names
        assert "P4" in result.fit_channel_names
        assert "P5" in result.fit_channel_names


class TestSgpsChannel:
    """Tests for SgpsChannel dataclass."""

    def test_effective_mev_geometric_mean(self):
        ch = SgpsChannel("P4", 15.0, 40.0, 10.0)
        expected = (15.0 * 40.0) ** 0.5
        assert ch.effective_mev == expected


class TestConstants:
    """Tests for module constants."""

    def test_channel_index_to_name_complete(self):
        # Should have indices 0-12 for P1-P11
        assert len(CHANNEL_INDEX_TO_NAME) == 13
        assert CHANNEL_INDEX_TO_NAME[0] == "P1"
        assert CHANNEL_INDEX_TO_NAME[12] == "P11"
        assert CHANNEL_INDEX_TO_NAME[3] == "P4"  # crosses 10 MeV

    def test_unit_constants(self):
        assert PFU == "protons/(cm^2 sr s)"
        assert DIFFERENTIAL_PER_KEV == "protons/(cm^2 sr keV s)"
        assert DIFFERENTIAL_PER_MEV == "protons/(cm^2 sr MeV s)"


class TestSgpsGe10Result:
    """Tests for SgpsGe10Result dataclass."""

    def test_result_fields(self):
        result = SgpsGe10Result(
            flux_ge10_pfu=100.0,
            uncertainty_pfu=10.0,
            spectral_index=2.5,
            normalization=1000.0,
            fit_channel_names=("P4", "P5"),
            zero_channel_count=0,
            direct_lower_bound_pfu=90.0,
            integral_mev_10_500_pfu=85.0,
            integral_gt500_pfu=5.0,
        )

        assert result.flux_ge10_pfu == 100.0
        assert result.uncertainty_pfu == 10.0
        assert result.spectral_index == 2.5
        assert result.normalization == 1000.0
        assert result.fit_channel_names == ("P4", "P5")
        assert result.zero_channel_count == 0
        assert result.direct_lower_bound_pfu == 90.0
        assert result.integral_mev_10_500_pfu == 85.0
        assert result.integral_gt500_pfu == 5.0
        assert result.method == "power_law_loglog_sgps_v2"
        assert result.status == "provisional"