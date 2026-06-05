import uuid
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.models.property import Property, PropertyChange
from app.core.database import get_db

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("/")
def list_properties(
    state: str | None = Query(None),
    city: str | None = Query(None),
    max_price: float | None = Query(None),
    min_discount: float | None = Query(None),
    occupancy_status: str | None = Query(None),
    sale_modality: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Property).filter(Property.status == "active")
    if state:
        q = q.filter(Property.state == state.upper())
    if city:
        q = q.filter(Property.city.ilike(f"%{city}%"))
    if max_price:
        q = q.filter(Property.current_value <= max_price)
    if min_discount:
        q = q.filter(Property.discount_percent >= min_discount)
    if occupancy_status:
        q = q.filter(Property.occupancy_status == occupancy_status)
    if sale_modality:
        q = q.filter(Property.sale_modality.ilike(f"%{sale_modality}%"))

    total = q.count()
    items = q.order_by(Property.opportunity_score.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": items, "offset": offset, "limit": limit}


@router.get("/{property_id}")
def get_property(property_id: uuid.UUID, db: Session = Depends(get_db)):
    prop = db.query(Property).filter_by(id=property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    changes = (
        db.query(PropertyChange)
        .filter_by(property_id=property_id)
        .order_by(PropertyChange.detected_at.desc())
        .all()
    )
    return {"property": prop, "changes": changes}
