"""GOES SGPS differential-spectrum -> provisional >=10 MeV proton flux.

This is a physics transform over the existing GOES SGPS ingest. It does not
define or modify an ODCS contract.

Important:
* Stored SGPS differential values are per keV. The transform requires the
  caller to declare the input unit explicitly and converts keV -> MeV.
* Energy bounds are taken from the source rows whenever available.
* P4 is never treated as wholly >=10 MeV.
* The measured >500 MeV integral is required and is never silently replaced
  with zero.
* Non-finite values fail closed.
* Zero differential channels are excluded from the power-law fit and counted;
  they are not assigned an arbitrary positive floor.
* The direct measured contribution from bands wholly above 10 MeV plus the
  >500 MeV integral is enforced as a lower bound on the derived result.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite, log
from typing import Iterable, Mapping, Sequence

PFU = "protons/(cm^2 sr s)"
DIFFERENTIAL_PER_KEV = "protons/(cm^2 sr keV s)"
DIFFERENTIAL_PER_MEV = "protons/(cm^2 sr MeV s)"

# Repository/table channel-index convention established by the GOES ingest.
# Indices 0..12 correspond to the 13 differential channels. The final
# integral >500 MeV channel is represented separately by its integral field.
CHANNEL_INDEX_TO_NAME: dict[int, str] = {
    0: "P1", 1: "P2", 2: "P3", 3: "P4", 4: "P5", 5: "P6",
    6: "P7", 7: "P8A", 8: "P8B", 9: "P8C", 10: "P9", 11: "P10",
    12: "P11",
}


class SgpsDerivationError(ValueError):
    """Raised when SGPS input cannot support a physically meaningful result."""


@dataclass(frozen=True)
class SgpsChannel:
    name: str
    lower_mev: float
    upper_mev: float
    flux: float

    @property
    def effective_mev(self) -> float:
        return (self.lower_mev * self.upper_mev) ** 0.5


@dataclass(frozen=True)
class SgpsGe10Result:
    flux_ge10_pfu: float
    uncertainty_pfu: float | None
    spectral_index: float | None
    normalization: float | None
    fit_channel_names: tuple[str, ...]
    zero_channel_count: int
    direct_lower_bound_pfu: float
    integral_mev_10_500_pfu: float
    integral_gt500_pfu: float
    method: str = "power_law_loglog_sgps_v2"
    status: str = "provisional"


def _require_finite(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value):
        raise SgpsDerivationError(f"{name} must be finite")
    return value


def convert_differential_to_mev(value: float, units: str) -> float:
    """Convert an SGPS differential flux to per-MeV units.

    The repository's SGPS table stores per-keV values. A units string is
    mandatory so the factor 1000 cannot be applied implicitly.
    """
    value = _require_finite("differential_flux", value)
    if value < 0:
        raise SgpsDerivationError("differential_flux cannot be negative")

    if units == DIFFERENTIAL_PER_KEV:
        return value * 1000.0
    if units == DIFFERENTIAL_PER_MEV:
        return value
    raise SgpsDerivationError(f"unsupported differential-flux units: {units!r}")


def _validate_bounds(lower: float, upper: float) -> tuple[float, float]:
    lower = _require_finite("lower_mev", lower)
    upper = _require_finite("upper_mev", upper)
    if lower <= 0 or upper <= lower:
        raise SgpsDerivationError("energy bounds must satisfy 0 < lower < upper")
    return lower, upper


def _fit_loglog(points: Sequence[tuple[float, float]]) -> tuple[float, float, float]:
    if len(points) < 2:
        raise SgpsDerivationError("at least two positive channels are required")

    xs = [log(x) for x, _ in points]
    ys = [log(y) for _, y in points]
    xbar = sum(xs) / len(xs)
    ybar = sum(ys) / len(ys)
    sxx = sum((x - xbar) ** 2 for x in xs)
    if sxx <= 0:
        raise SgpsDerivationError("fit energies are degenerate")

    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / sxx
    intercept = ybar - slope * xbar
    residuals = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    rms = (sum(r * r for r in residuals) / len(residuals)) ** 0.5
    return exp(intercept), -slope, rms


def _integral_power_law(A: float, gamma: float, lower: float, upper: float) -> float:
    if abs(gamma - 1.0) < 1e-10:
        return A * log(upper / lower)
    return A * (upper ** (1.0 - gamma) - lower ** (1.0 - gamma)) / (1.0 - gamma)


def derive_ge10_pfu(
    channels: Iterable[SgpsChannel],
    gt500_pfu: float,
) -> SgpsGe10Result:
    """Derive >=10 MeV integral flux from source-calibrated channels.

    `channels` must already be converted to per-MeV differential units.
    `gt500_pfu` is the measured >500 MeV integral and is mandatory.
    """
    gt500 = _require_finite(">500 MeV integral flux", gt500_pfu)
    if gt500 < 0:
        raise SgpsDerivationError(">500 MeV integral flux cannot be negative")

    prepared: list[SgpsChannel] = []
    zero_count = 0
    for channel in channels:
        lower, upper = _validate_bounds(channel.lower_mev, channel.upper_mev)
        flux = _require_finite(f"{channel.name} flux", channel.flux)
        if flux < 0:
            raise SgpsDerivationError(f"{channel.name} flux cannot be negative")
        if flux == 0:
            zero_count += 1
            continue
        prepared.append(SgpsChannel(channel.name, lower, upper, flux))

    # The measured contribution from bands entirely above 10 MeV is a strict
    # subset of >=10 MeV. It therefore provides a physical lower bound.
    direct = gt500
    for c in prepared:
        if c.lower_mev >= 10.0:
            direct += c.flux * (c.upper_mev - c.lower_mev)

    # P4 crosses 10 MeV; do not use it as a direct lower-bound term.
    fit_channels = [
        c for c in prepared
        if c.lower_mev < 500.0 and c.upper_mev > 5.0
    ]

    if len(fit_channels) < 2:
        raise SgpsDerivationError("fewer than two positive channels are available for fit")

    A, gamma, rms_log = _fit_loglog(
        [(c.effective_mev, c.flux) for c in fit_channels]
    )

    integral_10_500 = _integral_power_law(A, gamma, 10.0, 500.0)
    raw_total = integral_10_500 + gt500
    total = max(raw_total, direct)

    # rms_log is explicitly not a complete measurement uncertainty. Do not
    # expose it as a precision claim. With fewer than three fit channels,
    # uncertainty is unavailable.
    uncertainty = total * rms_log if len(fit_channels) >= 3 else None

    return SgpsGe10Result(
        flux_ge10_pfu=total,
        uncertainty_pfu=uncertainty,
        spectral_index=gamma,
        normalization=A,
        fit_channel_names=tuple(c.name for c in fit_channels),
        zero_channel_count=zero_count,
        direct_lower_bound_pfu=direct,
        integral_mev_10_500_pfu=integral_10_500,
        integral_gt500_pfu=gt500,
    )


def channels_from_table_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    differential_units: str = DIFFERENTIAL_PER_KEV,
    mask_quality: bool = True,
) -> tuple[list[SgpsChannel], float]:
    """Convert one sensor/time group from goes_sgps_flux_avg5m rows.

    Expected row keys are the existing table representation:
      channel_index, flux, energy_lower_mev, energy_upper_mev,
      valid_sample_count, dqf_sum.

    The exact table adapter may rename the flux key to match the repository's
    DDL; keep this function as the only place that binds table columns to the
    physics transform.

    The >500 MeV integral is expected in a row whose channel_index is 13 and
    whose `flux` is already in PFU. If the repository uses a named integral
    column instead, map it here rather than weakening derive_ge10_pfu().
    """
    channels: list[SgpsChannel] = []
    gt500: float | None = None

    for row in rows:
        idx = int(row["channel_index"])
        raw = row.get("flux")
        if raw is None:
            raise SgpsDerivationError(f"missing flux for channel_index={idx}")

        if mask_quality:
            valid = row.get("valid_sample_count")
            dqf = row.get("dqf_sum")
            if valid is not None and int(valid) <= 0:
                continue
            if dqf is not None and int(dqf) != 0:
                continue

        value = _require_finite("table flux", float(raw))
        if idx == 13:
            gt500 = value
            continue

        name = CHANNEL_INDEX_TO_NAME.get(idx)
        if name is None:
            raise SgpsDerivationError(f"unknown SGPS channel_index={idx}")

        lower, upper = _validate_bounds(
            float(row["energy_lower_mev"]),
            float(row["energy_upper_mev"]),
        )
        converted = convert_differential_to_mev(value, differential_units)
        channels.append(SgpsChannel(name, lower, upper, converted))

    if gt500 is None:
        raise SgpsDerivationError("missing >500 MeV integral channel")

    return channels, gt500
