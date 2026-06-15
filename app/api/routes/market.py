"""Rotas de preços de mercado e cálculo de ROI."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.middleware.auth import get_current_user
from app.calculator.roi import ROIInput, ROIResult, calculate_roi
from app.core.database import get_db as get_session
from app.core.logging import logger
from app.models.property import Property
from app.services.fipezap import get_market_prices_for_city, get_selic_rate_async

router = APIRouter(prefix="/market", tags=["market"])


class MarketPriceOut(BaseModel):
    city: str
    uf: str
    property_type: str
    price_per_sqm: float
    reference_month: str
    source: str = "fipezap"


class ROIRequest(BaseModel):
    intention: str = "revenda"
    horizon_months: int = 60
    area_sqm: float | None = None
    reform_cost_per_sqm: float = 500.0
    selic_annual: float | None = None


class ROIResponse(BaseModel):
    roi_pct: float | None
    yield_annual_pct: float | None
    payback_months: float | None
    cdi_equivalent_pct: float
    net_gain_vs_cdi_pct: float | None
    assumptions: dict


@router.get("/prices", response_model=list[MarketPriceOut])
async def get_market_prices(
    city: str | None = None,
    uf: str | None = None,
    property_type: str = "Apartamento",
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    from app.models.property import MarketPrice  # lazy import to avoid circular

    q = session.query(MarketPrice)
    if city:
        q = q.filter(MarketPrice.city.ilike(f"%{city}%"))
    if uf:
        q = q.filter(MarketPrice.uf == uf.upper())
    if property_type:
        q = q.filter(MarketPrice.property_type == property_type)
    rows = q.order_by(MarketPrice.reference_month.desc()).limit(200).all()
    return [
        MarketPriceOut(
            city=r.city,
            uf=r.uf,
            property_type=r.property_type,
            price_per_sqm=float(r.price_per_sqm),
            reference_month=str(r.reference_month),
        )
        for r in rows
    ]


@router.post("/properties/{property_id}/roi", response_model=ROIResponse)
async def compute_roi(
    property_id: str,
    req: ROIRequest,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    prop = session.query(Property).filter_by(external_code=property_id).first()
    if not prop:
        try:
            import uuid as _uuid
            prop = session.query(Property).filter_by(id=_uuid.UUID(property_id)).first()
        except Exception:
            pass
    if not prop:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")

    selic = req.selic_annual
    if selic is None:
        try:
            selic = float(await get_selic_rate_async())
        except Exception:
            selic = 10.50

    market_row = get_market_prices_for_city(prop.city, prop.state, "Apartamento", session)
    market_sqm = float(market_row.price_per_sqm_sale) if (market_row and market_row.price_per_sqm_sale) else None
    market_sqm_rent = float(market_row.price_per_sqm_rent) if (market_row and market_row.price_per_sqm_rent) else None

    try:
        inp = ROIInput(
            lance_value=float(prop.current_value or 0),
            intention=req.intention,  # type: ignore[arg-type]
            horizon_months=req.horizon_months,
            selic_annual=selic,
            area_sqm=req.area_sqm or getattr(prop, "area_sqm", None) or 60.0,
            reform_cost_per_sqm=req.reform_cost_per_sqm,
            market_price_per_sqm_sale=market_sqm,
            market_price_per_sqm_rent=market_sqm_rent,
        )
        result: ROIResult = calculate_roi(inp)
    except Exception as exc:
        logger.error("market.roi_error", property_id=property_id, error=str(exc))
        raise HTTPException(status_code=422, detail=str(exc))

    return ROIResponse(
        roi_pct=result.roi_pct,
        yield_annual_pct=result.yield_annual_pct,
        payback_months=result.payback_months,
        cdi_equivalent_pct=result.cdi_equivalent_pct,
        net_gain_vs_cdi_pct=result.net_gain_vs_cdi_pct,
        assumptions=result.assumptions,
    )
