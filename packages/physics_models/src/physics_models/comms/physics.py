"""S-band downlink budget from Orion to a DSN 34-m antenna (ODCS 03 comms_model_output).

    EIRP   = 10·log10(P_rf) + G_tx
    FSPL   = 20·log10(4π·d·f/c)
    Pr     = EIRP − FSPL + G_rx − L_misc
    Eb/N0  = Pr − N0 − 10·log10(R) − L_impl,   N0 = 10·log10(k·T_sys)
    margin = Eb/N0 − required Eb/N0

Sourced (see the contract's authoritativeDefinitions): the 2216.5 MHz carrier and the
1939.4 kbps maximum rate (Artemis I decode, NASA O2O 2025), the DSN receive gain and
system noise temperature (DSN 810-005 module 104). Orion's RF power and antenna gain are
not published, so their product (EIRP) is calibrated: the maximum rate closes with the
operational margin at 410,000 km, matching NASA's "up to ~2 Mb/s from lunar ranges".
"""

from dataclasses import dataclass
from math import log10, pi
from typing import Literal

SPEED_OF_LIGHT_M_S = 299_792_458.0
BOLTZMANN_DBW_PER_K_HZ = 10 * log10(1.380649e-23)  # −228.60 dBW/(K·Hz)

CommState = Literal["NOMINAL", "DEGRADED", "NO_LINK"]


def compute_free_space_path_loss(distance_km: float, frequency_hz: float) -> float:
    """Free-space path loss (dB): 20·log10(4π·d·f/c)."""
    return 20 * log10(4 * pi * distance_km * 1e3 * frequency_hz / SPEED_OF_LIGHT_M_S)


def compute_noise_density(system_noise_temp_k: float) -> float:
    """Receiver noise power spectral density N0 = k·T_sys (dBW/Hz)."""
    return BOLTZMANN_DBW_PER_K_HZ + 10 * log10(system_noise_temp_k)


def compute_eb_n0(
    received_power_dbw: float,
    noise_density_dbw_hz: float,
    data_rate_kbps: float,
    implementation_loss_db: float,
) -> float:
    """Bit energy to noise density ratio (dB) at a given data rate."""
    return (
        received_power_dbw
        - noise_density_dbw_hz
        - 10 * log10(data_rate_kbps * 1e3)
        - implementation_loss_db
    )


def compute_rf_power(
    max_rf_power_w: float,
    available_power_w: float,
    transmitter_dc_power_w: float,
) -> float:
    """RF output the power headroom allows (contracts 03/04: power gates transmit power).

    Full power when the headroom covers the transmitter's DC draw, scaled linearly
    below that, 0 (transmitter off) with no headroom.
    """
    return max_rf_power_w * min(1.0, max(0.0, available_power_w) / transmitter_dc_power_w)


def compute_signal_quality(link_margin_db: float, span_db: float = 20.0) -> float:
    """Normalised link margin (ODCS 03): 0.0 at threshold, 1.0 at +span_db above it."""
    return min(1.0, max(0.0, link_margin_db / span_db))


@dataclass(frozen=True)
class CommsLink:
    """One tick of comms output; field names match SyntheticCommsOutput."""

    eirp_dbw: float
    free_space_path_loss_db: float
    received_power_dbw: float
    eb_n0_db: float
    link_margin_db: float
    data_rate_kbps: float
    signal_quality: float
    comm_state: CommState


@dataclass
class CommsModel:
    """Orion S-band downlink with adaptive data rate (stateless: one call per tick)."""

    # Spacecraft
    downlink_frequency_hz: float = 2216.5e6  # Artemis I decode
    max_rf_power_w: float = 10.0  # MODEL_ASSUMPTION: not published (Apollo USB: 5-20 W)
    tx_antenna_gain_dbi: float = 2.07  # calibrated: EIRP 12.07 dBW (see module docstring)
    transmitter_dc_power_w: float = 150.0  # contract 03 (available_power_w description)

    # DSN 34-m BWG receiver (DSN 810-005 module 104, Table 6, Rev. E)
    dsn_antenna_gain_dbi: float = 56.50  # 56.8 dBi at 2295 MHz, scaled by 20·log10(f/f0)
    system_noise_temp_k: float = 41.4  # DSS 34 diplexed 39.3 K + Canberra 25% weather 2.1 K

    # Losses and thresholds
    misc_loss_db: float = 0.5  # MODEL_ASSUMPTION: pointing, polarization, atmosphere
    implementation_loss_db: float = 1.0  # MODEL_ASSUMPTION
    required_eb_n0_db: float = 2.0  # CCSDS LDPC r=1/2 k=1024: 1.8-2.2 dB in decoder data
    operational_margin_db: float = 3.0  # policy: NOMINAL needs this much margin

    # Rate set, highest first: the sourced maximum, then contract 03's UNVERIFIED steps
    data_rates_kbps: tuple[float, ...] = (1939.4, 1250.0, 512.0, 256.0, 128.0, 64.0, 16.0)
    signal_quality_span_db: float = 20.0  # contract 03

    # Transmitter off (no headroom) is modelled as a negligible RF power so every field
    # stays finite (contract: no nulls) and the margin is far below 0 at any range.
    rf_power_off_w: float = 1e-12

    def step(
        self,
        earth_distance_km: float,
        available_power_w: float | None,
        plasma_noise_factor: float = 1.0,
    ) -> CommsLink:
        """Link budget for one tick.

        Args:
            earth_distance_km: Earth-to-spacecraft distance (km)
            available_power_w: Power headroom from the previous power tick (W);
                None before the first power tick (transmitter at full power)
            plasma_noise_factor: Quality multiplier from the radiation model (1.0 = none)

        The highest rate whose margin reaches operational_margin_db is NOMINAL. If none
        does, the lowest rate is DEGRADED while its margin is still above 0; otherwise
        NO_LINK (rate 0, budget reported at the lowest rate).
        """
        if available_power_w is None:
            rf_power_w = self.max_rf_power_w
        else:
            rf_power_w = compute_rf_power(
                self.max_rf_power_w, available_power_w, self.transmitter_dc_power_w
            )
        rf_power_w = max(rf_power_w, self.rf_power_off_w)

        eirp = 10 * log10(rf_power_w) + self.tx_antenna_gain_dbi
        fspl = compute_free_space_path_loss(earth_distance_km, self.downlink_frequency_hz)
        received = eirp - fspl + self.dsn_antenna_gain_dbi - self.misc_loss_db
        n0 = compute_noise_density(self.system_noise_temp_k)

        def margin_at(rate_kbps: float) -> tuple[float, float]:
            eb_n0 = compute_eb_n0(received, n0, rate_kbps, self.implementation_loss_db)
            return eb_n0, eb_n0 - self.required_eb_n0_db

        state: CommState = "NO_LINK"
        rate = min(self.data_rates_kbps)
        eb_n0, margin = margin_at(rate)
        for candidate in sorted(self.data_rates_kbps, reverse=True):
            candidate_eb_n0, candidate_margin = margin_at(candidate)
            if candidate_margin >= self.operational_margin_db:
                state, rate, eb_n0, margin = "NOMINAL", candidate, candidate_eb_n0, candidate_margin
                break
        else:
            if margin > 0.0:
                state = "DEGRADED"

        if state == "NO_LINK":
            data_rate, quality = 0.0, 0.0
        else:
            data_rate = rate
            quality = compute_signal_quality(margin, self.signal_quality_span_db) * plasma_noise_factor

        return CommsLink(
            eirp_dbw=eirp,
            free_space_path_loss_db=fspl,
            received_power_dbw=received,
            eb_n0_db=eb_n0,
            link_margin_db=margin,
            data_rate_kbps=data_rate,
            signal_quality=quality,
            comm_state=state,
        )
