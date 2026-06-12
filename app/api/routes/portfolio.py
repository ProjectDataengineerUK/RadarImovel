import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.middleware.auth import get_current_user, require_feature
from app.core.database import get_db
from app.models.portfolio import KANBAN_STAGES, PortfolioItem
from app.models.property import Property
from app.models.user import User

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class PortfolioItemIn(BaseModel):
    property_id: uuid.UUID
    stage: str = Field("monitorando", pattern=f"^({'|'.join(KANBAN_STAGES)})$")
    actual_purchase_price: float | None = Field(None, ge=0)
    actual_renovation_cost: float | None = Field(None, ge=0)
    actual_other_costs: float | None = Field(None, ge=0)
    notes: str | None = None
    custom_data: dict[str, Any] = Field(default_factory=dict)


class PortfolioItemPatch(BaseModel):
    stage: str | None = Field(None, pattern=f"^({'|'.join(KANBAN_STAGES)})$")
    actual_purchase_price: float | None = None
    actual_renovation_cost: float | None = None
    actual_other_costs: float | None = None
    notes: str | None = None
    custom_data: dict[str, Any] | None = None


@router.get("")
def list_portfolio(
    db: Session = Depends(get_db),
    user: User = Depends(require_feature("portfolio")),
):
    items = (
        db.query(PortfolioItem)
        .filter_by(user_id=user.id)
        .order_by(PortfolioItem.updated_at.desc())
        .all()
    )
    return {"items": items}


@router.post("", status_code=201)
def add_to_portfolio(
    body: PortfolioItemIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_feature("portfolio")),
):
    prop = db.query(Property).filter_by(id=body.property_id).first()
    if not prop:
        raise HTTPException(404, detail="Property not found")

    existing = db.query(PortfolioItem).filter_by(user_id=user.id, property_id=body.property_id).first()
    if existing:
        raise HTTPException(409, detail="Property already in portfolio")

    item = PortfolioItem(
        user_id=user.id,
        property_id=body.property_id,
        stage=body.stage,
        actual_purchase_price=body.actual_purchase_price,
        actual_renovation_cost=body.actual_renovation_cost,
        actual_other_costs=body.actual_other_costs,
        notes=body.notes,
        custom_data=body.custom_data,
    )
    db.add(item)
    db.flush()
    return item


@router.patch("/{item_id}")
def update_portfolio_item(
    item_id: uuid.UUID,
    body: PortfolioItemPatch,
    db: Session = Depends(get_db),
    user: User = Depends(require_feature("portfolio")),
):
    item = db.query(PortfolioItem).filter_by(id=item_id, user_id=user.id).first()
    if not item:
        raise HTTPException(404, detail="Portfolio item not found")

    for field, val in body.model_dump(exclude_none=True).items():
        setattr(item, field, val)
    db.flush()
    return item


@router.delete("/{item_id}", status_code=204)
def remove_from_portfolio(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_feature("portfolio")),
):
    item = db.query(PortfolioItem).filter_by(id=item_id, user_id=user.id).first()
    if not item:
        raise HTTPException(404, detail="Portfolio item not found")
    db.delete(item)
    db.flush()
