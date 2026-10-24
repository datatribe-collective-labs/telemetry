"""Backend API client for Streamlit prototype.

Connects to FastAPI backend at http://localhost:8000 by default.
All endpoints return Pydantic models from contracts package.
"""

from datetime import datetime
from typing import Any

import httpx
from contracts import (
    CloseApproachResponse,
    DonkiEventResponse,
    DsnSiteGeometryResponse,
    GoesIntegralProtonsResponse,
    HealthResponse,
    OrionEphemerisResponse,
    SyntheticPowerResponse,
    SyntheticStateResponse,
    SyntheticTelemetryPacket,
    SyntheticTelemetryPacketResponse,
    SyntheticThermalResponse,
)


class BackendAPI:
    """Async HTTP client for FastAPI backend."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _get(self, path: str, params: dict | None = None, response_model: Any = None) -> Any:
        client = await self._get_client()
        resp = await client.get(path, params=params)
        resp.raise_for_status()
        data = resp.json()
        if response_model:
            return response_model(**data)
        return data

    # =========================================================================
    # Synthetic Telemetry Endpoints
    # =========================================================================

    async def get_synthetic_state(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> SyntheticStateResponse:
        params = {"limit": limit, "offset": offset}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        return await self._get("/telemetry/synthetic/state", params, SyntheticStateResponse)

    async def get_synthetic_thermal(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        thermal_state: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> SyntheticThermalResponse:
        params = {"limit": limit, "offset": offset}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if thermal_state:
            params["thermal_state"] = thermal_state
        return await self._get("/telemetry/synthetic/thermal", params, SyntheticThermalResponse)

    async def get_synthetic_power(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        power_state: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> SyntheticPowerResponse:
        params = {"limit": limit, "offset": offset}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if power_state:
            params["power_state"] = power_state
        return await self._get("/telemetry/synthetic/power", params, SyntheticPowerResponse)

    async def get_synthetic_packet(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        all_nominal: bool | None = None,
        thermal_state: str | None = None,
        power_state: str | None = None,
        comm_state: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> SyntheticTelemetryPacketResponse:
        params = {"limit": limit, "offset": offset}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if all_nominal is not None:
            params["all_nominal"] = all_nominal
        if thermal_state:
            params["thermal_state"] = thermal_state
        if power_state:
            params["power_state"] = power_state
        if comm_state:
            params["comm_state"] = comm_state
        return await self._get("/telemetry/synthetic/packet", params, SyntheticTelemetryPacketResponse)

    async def get_latest_packet(self) -> SyntheticTelemetryPacket | None:
        data = await self._get("/telemetry/synthetic/latest")
        if data:
            return SyntheticTelemetryPacket(**data)
        return None

    # =========================================================================
    # Real Data Endpoints
    # =========================================================================

    async def get_orion_ephemeris(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> OrionEphemerisResponse:
        params = {"limit": limit, "offset": offset}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        return await self._get("/orion", params, OrionEphemerisResponse)

    async def get_goes_protons(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> GoesIntegralProtonsResponse:
        params = {"limit": limit, "offset": offset}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        return await self._get("/iswa-goes-protons", params, GoesIntegralProtonsResponse)

    async def get_dsn_geometry(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        site: str | None = None,
        complex: str | None = None,
        visible_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> DsnSiteGeometryResponse:
        params = {"limit": limit, "offset": offset}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if site:
            params["site"] = site
        if complex:
            params["complex"] = complex
        if visible_only:
            params["visible_only"] = "true"
        return await self._get("/dsn-geometry", params, DsnSiteGeometryResponse)

    async def get_close_approaches(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        dist_max_au: float = 0.05,
        designation: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> CloseApproachResponse:
        params = {"limit": limit, "offset": offset, "dist_max_au": dist_max_au}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if designation:
            params["designation"] = designation
        return await self._get("/close-approaches", params, CloseApproachResponse)

    async def get_donki_events(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        event_types: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> DonkiEventResponse:
        params = {"limit": limit, "offset": offset}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if event_types:
            params["event_types"] = event_types
        return await self._get("/donki", params, DonkiEventResponse)

    # =========================================================================
    # Health
    # =========================================================================

    async def health_check(self) -> HealthResponse:
        return await self._get("/health", response_model=HealthResponse)


# Sync wrapper for Streamlit (which runs in sync context)
import asyncio


def run_async(coro):
    """Run async function in sync context (for Streamlit)."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class SyncBackendAPI:
    """Synchronous wrapper for BackendAPI (Streamlit compatible)."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0):
        self._async = BackendAPI(base_url, timeout)

    def _run(self, coro):
        return run_async(coro)

    def get_synthetic_state(self, **kwargs) -> SyntheticStateResponse:
        return self._run(self._async.get_synthetic_state(**kwargs))

    def get_synthetic_thermal(self, **kwargs) -> SyntheticThermalResponse:
        return self._run(self._async.get_synthetic_thermal(**kwargs))

    def get_synthetic_power(self, **kwargs) -> SyntheticPowerResponse:
        return self._run(self._async.get_synthetic_power(**kwargs))

    def get_synthetic_packet(self, **kwargs) -> SyntheticTelemetryPacketResponse:
        return self._run(self._async.get_synthetic_packet(**kwargs))

    def get_latest_packet(self) -> SyntheticTelemetryPacket | None:
        return self._run(self._async.get_latest_packet())

    def get_orion_ephemeris(self, **kwargs) -> OrionEphemerisResponse:
        return self._run(self._async.get_orion_ephemeris(**kwargs))

    def get_goes_protons(self, **kwargs) -> GoesIntegralProtonsResponse:
        return self._run(self._async.get_goes_protons(**kwargs))

    def get_dsn_geometry(self, **kwargs) -> DsnSiteGeometryResponse:
        return self._run(self._async.get_dsn_geometry(**kwargs))

    def get_close_approaches(self, **kwargs) -> CloseApproachResponse:
        return self._run(self._async.get_close_approaches(**kwargs))

    def get_donki_events(self, **kwargs) -> DonkiEventResponse:
        return self._run(self._async.get_donki_events(**kwargs))

    def health_check(self) -> HealthResponse:
        return self._run(self._async.health_check())

    def close(self):
        self._run(self._async.close())


# Module-level instance for easy imports
_api_instance: SyncBackendAPI | None = None


def get_api(base_url: str = "http://localhost:8000") -> SyncBackendAPI:
    """Get or create singleton API client."""
    global _api_instance
    if _api_instance is None:
        _api_instance = SyncBackendAPI(base_url)
    return _api_instance