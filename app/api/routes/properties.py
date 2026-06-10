import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import Document
from app.models.property import Property, PropertyChange

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("")
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

    edital_doc = (
        db.query(Document)
        .filter_by(property_id=property_id, document_type="edital")
        .first()
    )
    edital_processed = bool(
        edital_doc
        and edital_doc.processing_status == "done"
        and edital_doc.ai_summary
    )
    edital = None
    if edital_processed:
        try:
            extraction = json.loads(edital_doc.ai_summary)
        except (TypeError, ValueError):
            extraction = {}
            edital_processed = False
        else:
            edital = {
                **extraction,
                "processing_status": edital_doc.processing_status,
                "processed_at": edital_doc.processed_at,
            }

    return {
        "property": prop,
        "changes": changes,
        "edital_processed": edital_processed,
        "edital": edital,
    }
