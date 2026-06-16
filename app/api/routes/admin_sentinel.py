"""Admin Sentinela — endpoints de observabilidade: DataOps, LLMOps e MLOps."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, text, case
from sqlalchemy.orm import Session

from app.api.middleware.auth import require_role
from app.core.database import get_db
from app.models.document import Document
from app.models.prediction import PricePrediction
from app.models.risk import PropertyRiskScore
from app.models.user import User
from app.models.property import Property

router = APIRouter(prefix="/admin/sentinel", tags=["admin-sentinel"])


@router.get("/llmops")
def get_llmops(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("operador")),
):
    """Métricas de LLMOps: processamento de editais com Gemini."""
    total = db.query(func.count(Document.id)).scalar() or 0
    pending = (
        db.query(func.count(Document.id))
        .filter(Document.processing_status == "pending")
        .scalar() or 0
    )

    processed_today = (
        db.query(func.count(Document.id))
        .filter(
            Document.processing_status == "processed",
            func.date(Document.processed_at) == func.current_date(),
        )
        .scalar() or 0
    )

    failed_today = (
        db.query(func.count(Document.id))
        .filter(
            Document.processing_status == "failed",
            func.date(Document.processed_at) == func.current_date(),
        )
        .scalar() or 0
    )

    total_processed = (
        db.query(func.count(Document.id))
        .filter(Document.processing_status == "processed")
        .scalar() or 0
    )
    total_failed = (
        db.query(func.count(Document.id))
        .filter(Document.processing_status == "failed")
        .scalar() or 0
    )

    attempted = total_processed + total_failed
    success_rate = round((total_processed / attempted) * 100, 1) if attempted > 0 else 100.0

    avg_confidence = (
        db.query(func.avg(Document.extraction_confidence))
        .filter(Document.extraction_confidence.isnot(None))
        .scalar()
    )

    # Distribuição de confiança
    high_conf = (
        db.query(func.count(Document.id))
        .filter(Document.extraction_confidence >= 0.8)
        .scalar() or 0
    )
    med_conf = (
        db.query(func.count(Document.id))
        .filter(Document.extraction_confidence >= 0.6, Document.extraction_confidence < 0.8)
        .scalar() or 0
    )
    low_conf = (
        db.query(func.count(Document.id))
        .filter(Document.extraction_confidence < 0.6, Document.extraction_confidence.isnot(None))
        .scalar() or 0
    )

    recent_errors = (
        db.query(Document)
        .filter(Document.processing_status == "failed")
        .order_by(Document.processed_at.desc())
        .limit(10)
        .all()
    )

    return {
        "total_documents": total,
        "pending": pending,
        "processed_today": processed_today,
        "failed_today": failed_today,
        "total_processed": total_processed,
        "total_failed": total_failed,
        "success_rate_pct": success_rate,
        "avg_confidence": round(float(avg_confidence), 3) if avg_confidence else None,
        "confidence_distribution": {
            "high": high_conf,
            "medium": med_conf,
            "low": low_conf,
        },
        "recent_errors": [
            {
                "id": str(e.id),
                "property_id": str(e.property_id) if e.property_id else None,
                "processing_error": e.processing_error,
                "processed_at": e.processed_at.isoformat() if e.processed_at else None,
            }
            for e in recent_errors
        ],
    }


@router.get("/mlops")
def get_mlops(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("operador")),
):
    """Métricas de MLOps: score de oportunidade, risco e predições de preço."""
    total_properties = db.query(func.count(Property.id)).scalar() or 0

    # ── Score de oportunidade ────────────────────────────────────────
    scored = (
        db.query(func.count(Property.id))
        .filter(Property.opportunity_score.isnot(None))
        .scalar() or 0
    )
    avg_score = (
        db.query(func.avg(Property.opportunity_score))
        .filter(Property.opportunity_score.isnot(None))
        .scalar()
    )

    score_dist = db.execute(text("""
        SELECT
            CASE
                WHEN opportunity_score BETWEEN 0 AND 19  THEN '0-19'
                WHEN opportunity_score BETWEEN 20 AND 39 THEN '20-39'
                WHEN opportunity_score BETWEEN 40 AND 59 THEN '40-59'
                WHEN opportunity_score BETWEEN 60 AND 79 THEN '60-79'
                ELSE '80-100'
            END AS band,
            COUNT(*) AS n
        FROM properties
        WHERE opportunity_score IS NOT NULL
        GROUP BY 1
        ORDER BY 1
    """)).fetchall()

    # ── Mapa de risco ────────────────────────────────────────────────
    risk_total = db.query(func.count(PropertyRiskScore.id)).scalar() or 0
    avg_risk = (
        db.query(func.avg(PropertyRiskScore.score_total)).scalar()
    )
    risk_by_level = (
        db.query(PropertyRiskScore.risk_level, func.count(PropertyRiskScore.id))
        .group_by(PropertyRiskScore.risk_level)
        .all()
    )
    latest_risk_version = (
        db.query(PropertyRiskScore.calculation_version)
        .order_by(PropertyRiskScore.calculated_at.desc())
        .limit(1)
        .scalar()
    )

    # ── Predições de preço ──────────────────────────────────────────
    pred_total = db.query(func.count(PricePrediction.id)).scalar() or 0
    pred_versions = (
        db.query(PricePrediction.model_version, func.count(PricePrediction.id))
        .group_by(PricePrediction.model_version)
        .all()
    )
    avg_drop_30d = (
        db.query(func.avg(PricePrediction.expected_drop_pct))
        .filter(PricePrediction.horizon == 30)
        .scalar()
    )

    return {
        "score": {
            "total_properties": total_properties,
            "scored": scored,
            "coverage_pct": round((scored / total_properties) * 100, 1) if total_properties else 0,
            "avg_score": round(float(avg_score), 1) if avg_score else None,
            "distribution": {r.band: r.n for r in score_dist},
        },
        "risk": {
            "total": risk_total,
            "coverage_pct": round((risk_total / total_properties) * 100, 1) if total_properties else 0,
            "avg_total_score": round(float(avg_risk), 1) if avg_risk else None,
            "by_level": {level: count for level, count in risk_by_level},
            "latest_version": latest_risk_version or "—",
        },
        "prediction": {
            "total": pred_total,
            "coverage_pct": round((pred_total / total_properties) * 100, 1) if total_properties else 0,
            "model_versions": [{"version": v, "count": c} for v, c in pred_versions],
            "avg_expected_drop_30d_pct": round(float(avg_drop_30d), 1) if avg_drop_30d else None,
        },
    }
