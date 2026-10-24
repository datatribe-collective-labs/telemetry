"""API routes for JPL Horizons DSN site geometry (Orion look angles)."""

from datetime import datetime
from typing import Annotated

from contracts import DsnSiteGeometry, DsnSiteGeometryResponse
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db import get_db

router = APIRouter(prefix="/dsn-geometry", tags=["dsn-geometry"])


@router.get("", response_model=DsnSiteGeometryResponse)
async def list_dsn_site_geometry(
    db: Annotated[Session, Depends(get_db)],
    date_from: datetime | None = Query(None, description="Start date (UTC)"),
    date_to: datetime | None = Query(None, description="End date (UTC)"),
    site: str | None = Query(None, description="Filter by DSN site (e.g., DSS-14)"),
    complex: str | None = Query(None, description="Filter by DSN complex (Goldstone, Canberra, Madrid)"),
    visible_only: bool = Query(False, description="Only return visible passes (elevation >= 10 deg)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> DsnSiteGeometryResponse:
    """List DSN site geometry records with optional filters."""
    conditions = []
    params: dict[str, object] = {}

    if date_from:
        conditions.append("epoch >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append("epoch < :date_to")
        params["date_to"] = date_to
    if site:
        conditions.append("site = :site")
        params["site"] = site
    if complex:
        conditions.append("complex = :complex")
        params["complex"] = complex
    if visible_only:
        conditions.append("visible = true")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Count total
    count_query = f"SELECT COUNT(*) FROM dsn_site_geometry {where_clause}"
    total = db.execute(text(count_query), params).scalar() or 0

    # Fetch items
    select_query = f"""
        SELECT target_id, site, complex, epoch,
               azimuth_deg, elevation_deg, range_km, range_rate_kms,
               light_time_s, visible, ingested_at
        FROM dsn_site_geometry
        {where_clause}
        ORDER BY epoch, site
        LIMIT :limit OFFSET :offset
    """
    params["limit"] = limit
    params["offset"] = offset

    result = db.execute(text(select_query), params)
    items = [DsnSiteGeometry.model_validate(dict(row._mapping)) for row in result]

    return DsnSiteGeometryResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{target_id}/{site}/{epoch}", response_model=DsnSiteGeometry)
async def get_dsn_site_geometry(
    target_id: str,
    site: str,
    epoch: datetime,
    db: Annotated[Session, Depends(get_db)],
) -> DsnSiteGeometry:
    """Get a specific DSN site geometry record by primary key."""
    query = """
        SELECT target_id, site, complex, epoch,
               azimuth_deg, elevation_deg, range_km, range_rate_kms,
               light_time_s, visible, ingested_at
        FROM dsn_site_geometry
        WHERE target_id = :target_id AND site = :site AND epoch = :epoch
    """
    result = db.execute(text(query), {"target_id": target_id, "site": site, "epoch": epoch})
    row = result.first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="DSN site geometry record not found")

    return DsnSiteGeometry.model_validate(dict(row._mapping))