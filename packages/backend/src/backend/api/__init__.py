"""Backend API package."""

from fastapi import FastAPI

from backend.api.routes import (
    close_approaches,
    donki,
    health,
    iswa_goes_protons,
    jpl_dsn_geometry,
    mission_events,
    oem,
    orion,
    synthetic,
)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Telemetry API",
        description=(
            "API for querying NASA/JPL telemetry data (close approaches, Orion ephemeris, "
            "space weather, ISWA GOES protons, DSN geometry) AND synthetic telemetry from "
            "physics models (Artemis II digital twin)"
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(close_approaches.router)
    app.include_router(orion.router)
    app.include_router(donki.router)
    app.include_router(iswa_goes_protons.router)
    app.include_router(jpl_dsn_geometry.router)
    app.include_router(oem.router)
    app.include_router(mission_events.router)
    app.include_router(synthetic.router)

    return app


app = create_app()