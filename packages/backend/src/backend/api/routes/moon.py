"""API routes for the JPL Horizons Moon ephemeris (Earth-centred, EME2000).

Written by `pipelines.ingest.jpl_moon`; the Digital Twin dashboard draws it on
Orion's trajectory map.
"""

from datetime import datetime
from typing import Annotated

from contracts import MoonEphemeris, MoonEphemerisResponse
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db import get_db

router = APIRouter(prefix="/moon", tags=["moon"])


@router.get("", response_model=MoonEphemerisResponse)
async def list_moon_ephemeris(
    db: Annotated[Session, Depends(get_db)],
    date_from: datetime | None = Query(None, description="Start date (UTC)"),
    date_to: datetime | None = Query(None, description="End date (UTC)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> MoonEphemerisResponse:
    """List Moon ephemeris records in epoch order, with optional time filters."""
    conditions = []
    params: dict[str, object] = {}
    if date_from:
        conditions.append("epoch >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append("epoch <= :date_to")
        params["date_to"] = date_to
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    total = db.execute(text(f"SELECT COUNT(*) FROM moon_ephemeris {where_clause}"), params).scalar() or 0

    params["limit"] = limit
    params["offset"] = offset
    result = db.execute(
        text(f"""
            SELECT epoch, jd, x_km, y_km, z_km, vx_kms, vy_kms, vz_kms, range_km
            FROM moon_ephemeris
            {where_clause}
            ORDER BY epoch
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    items = [MoonEphemeris.model_validate(dict(row._mapping)) for row in result]
    return MoonEphemerisResponse(items=items, total=total, limit=limit, offset=offset)
