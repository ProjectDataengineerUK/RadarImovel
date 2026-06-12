"""GET /radar-index — Índice público de deságio por estado/banco (sem autenticação)."""
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.prediction import RadarIndex

router = APIRouter(prefix="/radar-index", tags=["radar-index"])


class RadarIndexEntry(BaseModel):
    period: str
    state: str
    bank_code: str | None
    property_type: str | None
    sample_size: int
    avg_discount_pct: float
    median_discount_pct: float
    p25_discount_pct: float | None
    p75_discount_pct: float | None


class RadarIndexResponse(BaseModel):
    period: str
    entries: list[RadarIndexEntry]


@router.get("", response_model=RadarIndexResponse)
def get_radar_index(
    period: str | None = Query(None, description="Período YYYY-MM; padrão = mais recente"),
    state: str | None = Query(None, description="Filtro por UF (ex: SP)"),
    db: Session = Depends(get_db),
) -> Any:
    q = db.query(RadarIndex)

    if period:
        q = q.filter(RadarIndex.period == period)
    else:
        latest = (
            db.query(RadarIndex.period)
            .order_by(RadarIndex.period.desc())
            .first()
        )
        if latest:
            q = q.filter(RadarIndex.period == latest[0])
            period = latest[0]
        else:
            return RadarIndexResponse(period="", entries=[])

    if state:
        q = q.filter(RadarIndex.state == state.upper())

    rows = q.order_by(RadarIndex.state, RadarIndex.bank_code).all()

    return RadarIndexResponse(
        period=period or "",
        entries=[
            RadarIndexEntry(
                period=r.period,
                state=r.state,
                bank_code=r.bank_code,
                property_type=r.property_type,
                sample_size=r.sample_size,
                avg_discount_pct=float(r.avg_discount_pct),
                median_discount_pct=float(r.median_discount_pct),
                p25_discount_pct=float(r.p25_discount_pct) if r.p25_discount_pct else None,
                p75_discount_pct=float(r.p75_discount_pct) if r.p75_discount_pct else None,
            )
            for r in rows
        ],
    )
