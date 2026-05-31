from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.core.database import get_db
from app.models.property import Property
from app.models.user import Alert

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status")
def collector_status(db: Session = Depends(get_db)):
    """Status dos coletores: última coleta, imóveis ativos, alertas enviados."""
    total_active = db.query(func.count(Property.id)).filter(Property.status == "active").scalar()
    last_seen = db.query(func.max(Property.last_seen_at)).scalar()
    first_seen_today = db.query(func.count(Property.id)).filter(
        func.date(Property.first_seen_at) == func.current_date()
    ).scalar()
    alerts_today = db.query(func.count(Alert.id)).filter(
        func.date(Alert.created_at) == func.current_date()
    ).scalar()

    return {
        "total_active_properties": total_active,
        "last_collection_at": last_seen,
        "new_today": first_seen_today,
        "alerts_sent_today": alerts_today,
    }


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as exc:
        return {"status": "error", "db": str(exc)}
