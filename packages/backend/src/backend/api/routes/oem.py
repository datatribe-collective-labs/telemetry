"""API routes for NASA OEM ephemeris arcs (Artemis II planning data)."""

from datetime import datetime
from typing import Annotated

from contracts import OemStateVector, OemStateVectorResponse
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db import get_db

router = APIRouter(prefix="/oem", tags=["oem"])


@router.get("/arcs", response_model=list[str])
async def list_oem_arcs(db: Annotated[Session, Depends(get_db)]) -> list[str]:
    """List ingested OEM planning arc identifiers."""
    rows = db.execute(text("SELECT DISTINCT arc_id FROM oem_state_vectors ORDER BY arc_id")).scalars().all()
    return list(rows)


@router.get("", response_model=OemStateVectorResponse)
async def list_oem_state_vectors(
    db: Annotated[Session, Depends(get_db)],
    arc_id: str | None = Query(None, description="Arc to query; default = lexically latest arc id"),
    date_from: datetime | None = Query(None, description="Start date (UTC)"),
    date_to: datetime | None = Query(None, description="End date (UTC)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> OemStateVectorResponse:
    """List OEM state vectors for one arc (latest by default)."""
    if arc_id is None:
        arc_id = db.execute(text("SELECT max(arc_id) FROM oem_state_vectors")).scalar()
        if arc_id is None:
            raise HTTPException(status_code=404, detail="No OEM arcs ingested")

    conditions = ["arc_id = :arc_id"]
    params: dict[str, object] = {"arc_id": arc_id}
    if date_from:
        conditions.append("epoch >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append("epoch < :date_to")
        params["date_to"] = date_to
    where_clause = "WHERE " + " AND ".join(conditions)

    total = db.execute(text(f"SELECT COUNT(*) FROM oem_state_vectors {where_clause}"), params).scalar() or 0
    rows = db.execute(
        text(f"""
            SELECT arc_id, epoch, x_km, y_km, z_km, vx_kms, vy_kms, vz_kms, range_km, speed_kms
            FROM oem_state_vectors
            {where_clause}
            ORDER BY epoch
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": limit, "offset": offset},
    ).mappings().all()

    return OemStateVectorResponse(
        items=[OemStateVector.model_validate(dict(r)) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
