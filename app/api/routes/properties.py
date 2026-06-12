import csv
import io
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.middleware.auth import get_current_user, require_feature
from app.core.database import get_db
from app.models.document import Document
from app.models.bank import Bank
from app.models.property import Property, PropertyChange, PropertyOffer
from app.models.prediction import PricePrediction
from app.models.user import User
from app.schemas.matricula import MatriculaOut

router = APIRouter(prefix="/properties", tags=["properties"])

_EXPORT_COLS = [
    "id", "external_code", "bank", "state", "city", "address",
    "property_type", "current_value", "appraisal_value", "discount_percent",
    "opportunity_score", "sale_modality", "occupancy_status", "status",
    "official_url",
]


@router.get("", include_in_schema=True)
@router.get("/", include_in_schema=False)
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


@router.get("/export")
def export_properties(
    state: str | None = Query(None),
    city: str | None = Query(None),
    max_price: float | None = Query(None),
    min_discount: float | None = Query(None),
    fmt: str = Query("csv", pattern="^(csv|xlsx)$"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_feature("export")),
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

    items = q.order_by(Property.opportunity_score.desc()).limit(5000).all()

    if fmt == "xlsx":
        return _export_xlsx(items)
    return _export_csv(items)


def _export_csv(items: list[Property]) -> StreamingResponse:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_EXPORT_COLS)
    writer.writeheader()
    for p in items:
        writer.writerow({
            "id": str(p.id),
            "external_code": p.external_code,
            "bank": p.bank.code if p.bank else "",
            "state": p.state,
            "city": p.city,
            "address": p.address or "",
            "property_type": p.property_type,
            "current_value": float(p.current_value),
            "appraisal_value": float(p.appraisal_value) if p.appraisal_value else "",
            "discount_percent": float(p.discount_percent) if p.discount_percent else "",
            "opportunity_score": p.opportunity_score or "",
            "sale_modality": p.sale_modality,
            "occupancy_status": p.occupancy_status,
            "status": p.status,
            "official_url": p.official_url or "",
        })
    output.seek(0)
    headers = {"Content-Disposition": "attachment; filename=radar_imoveis.csv"}
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)


def _export_xlsx(items: list[Property]) -> StreamingResponse:
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(500, detail="openpyxl não instalado")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Imóveis"
    ws.append(_EXPORT_COLS)
    for p in items:
        ws.append([
            str(p.id),
            p.external_code,
            p.bank.code if p.bank else "",
            p.state,
            p.city,
            p.address or "",
            p.property_type,
            float(p.current_value),
            float(p.appraisal_value) if p.appraisal_value else None,
            float(p.discount_percent) if p.discount_percent else None,
            p.opportunity_score,
            p.sale_modality,
            p.occupancy_status,
            p.status,
            p.official_url or "",
        ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    headers = {"Content-Disposition": "attachment; filename=radar_imoveis.xlsx"}
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)


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
            edital_processed = False
        else:
            edital = {
                **extraction,
                "processing_status": edital_doc.processing_status,
                "processed_at": edital_doc.processed_at,
            }

    # Matrícula
    matricula_doc = (
        db.query(Document)
        .filter_by(property_id=property_id, document_type="matricula")
        .first()
    )
    matricula: MatriculaOut | None = None
    if matricula_doc and matricula_doc.processing_status == "done" and matricula_doc.ai_summary:
        try:
            raw = json.loads(matricula_doc.ai_summary)
            model_used = raw.pop("_model_used", None)
            matricula = MatriculaOut(
                **raw,
                model_used=model_used,
                processed_at=str(matricula_doc.processed_at) if matricula_doc.processed_at else None,
            )
        except Exception:
            pass

    return {
        "property": prop,
        "changes": changes,
        "edital_processed": edital_processed,
        "edital": edital,
        "matricula": matricula,
    }


@router.get("/{property_id}/predictions")
def get_predictions(
    property_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_feature("price_forecast")),
):
    prop = db.query(Property).filter_by(id=property_id).first()
    if not prop:
        raise HTTPException(status_code=404)
    preds = (
        db.query(PricePrediction)
        .filter_by(property_id=property_id)
        .order_by(PricePrediction.horizon)
        .all()
    )
    return [
        {
            "horizon": p.horizon,
            "probability": float(p.probability),
            "expected_drop_pct": float(p.expected_drop_pct),
            "model_version": p.model_version,
            "basis": p.basis,
            "computed_at": p.computed_at.isoformat(),
        }
        for p in preds
    ]


@router.get("/{property_id}/offers")
def get_offers(property_id: uuid.UUID, db: Session = Depends(get_db)):
    prop = db.query(Property).filter_by(id=property_id).first()
    if not prop:
        raise HTTPException(status_code=404)
    offers = (
        db.query(PropertyOffer)
        .filter_by(property_id=property_id, active=True)
        .order_by(PropertyOffer.price)
        .all()
    )
    result = []
    for o in offers:
        source = db.get(Bank, o.source_id)
        result.append({
            "id": str(o.id),
            "source_name": source.name if source else o.source_id,
            "price": float(o.price),
            "modality": o.modality,
            "auction_date": o.auction_date.isoformat() if o.auction_date else None,
            "official_url": o.official_url,
        })
    return result
