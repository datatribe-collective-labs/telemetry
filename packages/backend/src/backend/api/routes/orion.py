"""API routes for JPL Horizons Orion spacecraft ephemeris."""

from datetime import datetime
from typing import Annotated

from contracts import OrionEphemeris, OrionEphemerisResponse
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db import get_db

router = APIRouter(prefix="/orion", tags=["orion"])


@router.get("", response_model=OrionEphemerisResponse)
async def list_orion_ephemeris(
    db: Annotated[Session, Depends(get_db)],
    date_from: datetime | None = Query(None, description="Start date (UTC)"),
    date_to: datetime | None = Query(None, description="End date (UTC)"),
    target_id: str = Query("-1024", description="Target ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> OrionEphemerisResponse:
    """List Orion ephemeris records with optional filters."""
    conditions = ["target_id = :target_id"]
    params: dict[str, object] = {"target_id": target_id}

    if date_from:
        conditions.append("epoch >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append("epoch <= :date_to")
        params["date_to"] = date_to

    where_clause = "WHERE " + " AND ".join(conditions)

    # Count total
    count_query = f"SELECT COUNT(*) FROM orion_ephemeris {where_clause}"
    total = db.execute(text(count_query), params).scalar() or 0

    # Fetch items
    select_query = f"""
        SELECT target_id, epoch, jd, x_km, y_km, z_km,
               vx_kms, vy_kms, vz_kms, speed_kms,
               light_time_s, range_km, range_rate_kms
        FROM orion_ephemeris
        {where_clause}
        ORDER BY epoch
        LIMIT :limit OFFSET :offset
    """
    params["limit"] = limit
    params["offset"] = offset

    result = db.execute(text(select_query), params)
    items = [OrionEphemeris.model_validate(dict(row._mapping)) for row in result]

    return OrionEphemerisResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{target_id}/{epoch}", response_model=OrionEphemeris)
async def get_orion_ephemeris(
    target_id: str,
    epoch: datetime,
    db: Annotated[Session, Depends(get_db)],
) -> OrionEphemeris:
    """Get a specific Orion ephemeris record by primary key."""
    query = """
        SELECT target_id, epoch, jd, x_km, y_km, z_km,
               vx_kms, vy_kms, vz_kms, speed_kms,
               light_time_s, range_km, range_rate_kms
        FROM orion_ephemeris
        WHERE target_id = :target_id AND epoch = :epoch
    """
    result = db.execute(text(query), {"target_id": target_id, "epoch": epoch})
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Orion ephemeris record not found")

    return OrionEphemeris.model_validate(dict(row._mapping))