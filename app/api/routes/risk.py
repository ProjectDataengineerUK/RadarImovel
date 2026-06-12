import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.middleware.auth import get_current_user, require_role
from app.core.database import get_db
from app.models.property import Property
from app.models.risk import PropertyRiskScore

router = APIRouter(prefix="", tags=["risk"])


@router.get("/properties/{property_id}/risk")
def get_property_risk(
    property_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    score = db.query(PropertyRiskScore).filter_by(property_id=property_id).first()
    if not score:
        raise HTTPException(status_code=404, detail="Risk score not calculated yet")
    return _serialize_score(score)


@router.get("/map/risk-heatmap")
def risk_heatmap(
    uf: str | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    q = (
        db.query(
            Property.city,
            Property.state,
            func.avg(PropertyRiskScore.score_total).label("risk_avg"),
            func.count(Property.id).label("property_count"),
        )
        .join(PropertyRiskScore, PropertyRiskScore.property_id == Property.id)
        .filter(Property.status == "active")
        .group_by(Property.city, Property.state)
    )
    if uf:
        q = q.filter(Property.state == uf.upper())

    rows = q.all()
    features = [
        {
            "type": "Feature",
            "properties": {
                "city": r.city,
                "state": r.state,
                "risk_avg": round(float(r.risk_avg), 1),
                "property_count": r.property_count,
            },
            "geometry": None,
        }
        for r in rows
    ]
    return {"type": "FeatureCollection", "features": features}


@router.get("/map/layers/{layer_type}")
def get_geodata_layer(
    layer_type: str,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = db.execute(
        text(
            "SELECT name, attributes, ST_AsGeoJSON(geom)::json AS geometry "
            "FROM risk_geodata_layers WHERE layer_type = :lt"
        ),
        {"lt": layer_type},
    ).fetchall()
    features = [
        {
            "type": "Feature",
            "properties": {"name": r.name, **(r.attributes or {})},
            "geometry": r.geometry,
        }
        for r in rows
    ]
    return {"type": "FeatureCollection", "features": features}


@router.get("/properties/{property_id}/risk/report")
def download_risk_report(
    property_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    prop = db.query(Property).filter_by(id=property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    score = db.query(PropertyRiskScore).filter_by(property_id=property_id).first()
    if not score:
        raise HTTPException(status_code=404, detail="Risk score not calculated yet")

    from app.risk.pdf_report import generate_report

    property_data = {
        "address": prop.address,
        "city": prop.city,
        "state": prop.state,
        "property_type": prop.property_type,
        "current_value": float(prop.current_value),
        "discount_percent": float(prop.discount_percent) if prop.discount_percent else None,
        "occupancy_status": prop.occupancy_status,
        "sale_modality": prop.sale_modality,
    }
    score_data = _serialize_score(score)
    pdf_bytes = generate_report(property_data, score_data)

    filename = f"due_diligence_{property_id}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/admin/recalculate-risk/{property_id}")
def recalculate_risk(
    property_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin")),
):
    from app.core.config import get_settings
    import json
    from google.cloud import pubsub_v1

    settings = get_settings()
    prop = db.query(Property).filter_by(id=property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(settings.pubsub_project_id, settings.pubsub_topic_risk)
    event = {
        "property_id": str(property_id),
        "lat": float(prop.latitude) if prop.latitude else None,
        "lng": float(prop.longitude) if prop.longitude else None,
        "city": prop.city,
        "state": prop.state,
    }
    publisher.publish(topic_path, json.dumps(event).encode())
    return {"status": "queued", "property_id": str(property_id)}


def _serialize_score(score: PropertyRiskScore) -> dict:
    indicators_serialized = {}
    raw = score.indicators or {}
    for k, v in raw.items():
        if isinstance(v, dict):
            indicators_serialized[k] = v
        else:
            indicators_serialized[k] = v.model_dump() if hasattr(v, "model_dump") else v

    return {
        "property_id": str(score.property_id),
        "score_total": float(score.score_total),
        "risk_level": score.risk_level,
        "score_juridico": float(score.score_juridico),
        "score_fundiario": float(score.score_fundiario),
        "score_fiscal": float(score.score_fiscal),
        "score_ocupacao": float(score.score_ocupacao),
        "score_socioeconomico": float(score.score_socioeconomico),
        "score_mercado": float(score.score_mercado),
        "score_partial": score.score_partial,
        "indicators": indicators_serialized,
        "sources_consulted": score.sources_consulted or [],
        "calculation_version": score.calculation_version,
        "calculated_at": score.calculated_at.isoformat() if score.calculated_at else None,
    }
