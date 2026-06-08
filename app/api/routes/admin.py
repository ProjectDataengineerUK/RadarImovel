import subprocess
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.core.database import get_db
from app.models.property import Property
from app.models.user import Alert
from app.core.config import get_settings

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


class CollectRequest(BaseModel):
    uf: str


@router.post("/collect")
def trigger_collect(req: CollectRequest):
    """Dispara o Cloud Run Job de coleta para uma UF."""
    settings = get_settings()
    uf = req.uf.upper()
    valid_ufs = {"AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
                 "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"}
    if uf not in valid_ufs:
        raise HTTPException(status_code=400, detail=f"UF inválida: {uf}")

    project = settings.pubsub_project_id or "radarimovel"
    cmd = [
        "gcloud", "run", "jobs", "execute", "radar-collect-caixa",
        f"--region=us-central1",
        f"--project={project}",
        f"--update-env-vars=UF={uf}",
        "--async",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        return {"started": True, "uf": uf}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as exc:
        return {"status": "error", "db": str(exc)}
