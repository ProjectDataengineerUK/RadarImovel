"""GET /radar-index — Índice público de deságio por estado/banco/município."""
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
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


class CityIndexEntry(BaseModel):
    city: str
    uf: str
    sample_size: int
    avg_discount_pct: float
    median_discount_pct: float
    trend_delta: float | None
    trend: str | None = None  # "up" | "down" | "stable"
    market_price_per_sqm: float | None = None


class CityIndexResponse(BaseModel):
    entries: list[CityIndexEntry]


class HotspotEntry(BaseModel):
    city: str
    uf: str
    sample_size: int
    avg_discount_pct: float
    trend_delta: float | None


@router.get("", response_model=RadarIndexResponse)
def get_radar_index(
    period: str | None = Query(None, description="Período YYYY-MM; padrão = mais recente"),
    state: str | None = Query(None, description="Filtro por UF (ex: SP)"),
    granularity: Literal["state", "city"] = Query("state", description="Agregação por estado ou município"),
    db: Session = Depends(get_db),
) -> Any:
    if granularity == "city":
        return _get_city_index(state, db)

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


def _trend_label(delta: float | None) -> str | None:
    if delta is None:
        return None
    if delta > 1.0:
        return "up"
    if delta < -1.0:
        return "down"
    return "stable"


def _get_city_index(state: str | None, db: Session) -> CityIndexResponse:
    """Agrega deságio por município nos últimos 2 meses, com tendência e preço FipeZap."""
    uf_filter = "AND state = :uf" if state else ""
    params: dict = {"uf": state.upper()} if state else {}
    sql = text(f"""
        WITH monthly AS (
            SELECT
                city,
                state AS uf,
                DATE_TRUNC('month', first_seen_at) AS period,
                COUNT(*) AS sample_size,
                AVG(discount_percent) AS avg_discount_pct,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY discount_percent) AS median_discount_pct
            FROM properties
            WHERE
                discount_percent IS NOT NULL
                AND first_seen_at >= NOW() - INTERVAL '2 months'
                AND city IS NOT NULL
                {uf_filter}
            GROUP BY city, state, DATE_TRUNC('month', first_seen_at)
        ),
        with_trend AS (
            SELECT
                city,
                uf,
                period,
                sample_size,
                avg_discount_pct,
                median_discount_pct,
                avg_discount_pct - LAG(avg_discount_pct) OVER (
                    PARTITION BY city, uf ORDER BY period
                ) AS trend_delta
            FROM monthly
        ),
        aggregated AS (
            SELECT city, uf, SUM(sample_size) AS sample_size,
                   AVG(avg_discount_pct) AS avg_discount_pct,
                   AVG(median_discount_pct) AS median_discount_pct,
                   MAX(trend_delta) AS trend_delta
            FROM with_trend
            WHERE period = (SELECT MAX(period) FROM monthly)
            GROUP BY city, uf
            ORDER BY avg_discount_pct DESC
            LIMIT 200
        )
        SELECT
            a.city, a.uf, a.sample_size, a.avg_discount_pct,
            a.median_discount_pct, a.trend_delta,
            m.price_per_sqm_sale AS market_price_per_sqm
        FROM aggregated a
        LEFT JOIN LATERAL (
            SELECT price_per_sqm_sale
            FROM market_prices
            WHERE LOWER(city) = LOWER(a.city) AND UPPER(uf) = UPPER(a.uf)
            ORDER BY reference_month DESC
            LIMIT 1
        ) m ON true
    """)
    rows = db.execute(sql, params).fetchall()
    return CityIndexResponse(
        entries=[
            CityIndexEntry(
                city=r.city,
                uf=r.uf,
                sample_size=r.sample_size,
                avg_discount_pct=float(r.avg_discount_pct),
                median_discount_pct=float(r.median_discount_pct),
                trend_delta=float(r.trend_delta) if r.trend_delta is not None else None,
                trend=_trend_label(float(r.trend_delta) if r.trend_delta is not None else None),
                market_price_per_sqm=float(r.market_price_per_sqm) if r.market_price_per_sqm is not None else None,
            )
            for r in rows
        ]
    )


@router.get("/hotspots", response_model=list[HotspotEntry])
def get_hotspots(
    min_sample: int = Query(5, description="Mínimo de imóveis no período"),
    limit: int = Query(10, description="Top N municípios"),
    db: Session = Depends(get_db),
) -> Any:
    """Top municípios com maior deságio médio nos últimos 30 dias (mín. sample_size imóveis)."""
    sql = text("""
        SELECT
            city,
            state AS uf,
            COUNT(*) AS sample_size,
            AVG(discount_percent) AS avg_discount_pct,
            AVG(discount_percent) - LAG(AVG(discount_percent)) OVER (
                PARTITION BY city, state
                ORDER BY DATE_TRUNC('month', first_seen_at)
            ) AS trend_delta
        FROM properties
        WHERE
            discount_percent IS NOT NULL
            AND first_seen_at >= NOW() - INTERVAL '30 days'
            AND city IS NOT NULL
        GROUP BY city, state, DATE_TRUNC('month', first_seen_at)
        HAVING COUNT(*) >= :min_sample
        ORDER BY avg_discount_pct DESC
        LIMIT :limit
    """)
    rows = db.execute(sql, {"min_sample": min_sample, "limit": limit}).fetchall()
    return [
        HotspotEntry(
            city=r.city,
            uf=r.uf,
            sample_size=r.sample_size,
            avg_discount_pct=float(r.avg_discount_pct),
            trend_delta=float(r.trend_delta) if r.trend_delta is not None else None,
        )
        for r in rows
    ]
