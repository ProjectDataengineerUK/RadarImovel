import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.middleware.auth import get_current_user, require_feature
from app.calculator.engine import ViabilityResult, calculate_viability
from app.core.database import get_db
from app.models.property import Property
from app.models.user import User

router = APIRouter(prefix="/properties", tags=["calculator"])


class ViabilityRequest(BaseModel):
    monthly_condo: float | None = Field(None, ge=0)
    area_m2: float | None = Field(None, gt=0)
    existing_debt: float = Field(0.0, ge=0)
    hold_years: int = Field(5, ge=1, le=30)


def _result_to_dict(r: ViabilityResult) -> dict[str, Any]:
    return {
        "scenario": r.scenario,
        "purchase_price": r.purchase_price,
        "acquisition_costs": round(r.acquisition_costs, 2),
        "renovation_cost": round(r.renovation_cost, 2),
        "total_investment": round(r.total_investment, 2),
        "sale_price_estimate": round(r.sale_price_estimate, 2),
        "gross_margin_pct": round(r.gross_margin_pct, 2),
        "holding_costs": round(r.holding_costs, 2),
        "net_profit": round(r.net_profit, 2),
        "roi_pct": round(r.roi_pct, 2),
        "payback_months": r.payback_months,
        "monthly_rent": round(r.monthly_rent, 2),
        "annual_gross_yield_pct": round(r.annual_gross_yield_pct, 2),
        "annual_net_yield_pct": round(r.annual_net_yield_pct, 2),
        "exit_value": round(r.exit_value, 2),
        "irr_annual_pct": round(r.irr_annual_pct, 2) if r.irr_annual_pct is not None else None,
        "npv": round(r.npv, 2),
        "max_price_to_breakeven": round(r.max_price_to_breakeven, 2),
        "discount_vs_appraisal_pct": round(r.discount_vs_appraisal_pct, 2),
        "viable": r.viable,
        "warnings": r.warnings,
    }


@router.post("/{property_id}/viability")
def calculate_property_viability(
    property_id: uuid.UUID,
    body: ViabilityRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_feature("calculator")),
):
    prop = db.query(Property).filter_by(id=property_id, status="active").first()
    if not prop:
        raise HTTPException(404, detail="Property not found")

    appraisal = float(prop.appraisal_value) if prop.appraisal_value else None
    purchase = float(prop.current_value)

    results = calculate_viability(
        purchase_price=purchase,
        appraisal_value=appraisal,
        state=prop.state,
        property_type=prop.property_type or "imovel",
        area_m2=body.area_m2,
        monthly_condo=body.monthly_condo,
        existing_debt=body.existing_debt,
        hold_years=body.hold_years,
        db=db,
    )

    return {
        "property_id": str(property_id),
        "scenarios": [_result_to_dict(r) for r in results],
    }
