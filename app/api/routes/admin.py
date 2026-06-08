from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.core.database import get_db
from app.models.property import Property
from app.models.user import Alert

router = APIRouter(prefix="/admin", tags=["admin"])

VALID_UFS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
}


@router.get("/status")
def collector_status(db: Session = Depends(get_db)):
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


def _run_collect(uf: str) -> None:
    """Executa coleta Caixa em background reutilizando o job existente."""
    import structlog
    log = structlog.get_logger()
    try:
        from jobs.collect_caixa import run as collect_run
        collect_run(uf, fetch_detail=False)
    except SystemExit as exc:
        log.error("admin.collect.exit", uf=uf, code=exc.code)
    except Exception as exc:
        log.error("admin.collect.error", uf=uf, error=str(exc))


@router.post("/collect")
def trigger_collect(
    req: CollectRequest,
    background_tasks: BackgroundTasks,
):
    uf = req.uf.upper()
    if uf not in VALID_UFS:
        raise HTTPException(status_code=400, detail=f"UF inválida: {uf}")

    background_tasks.add_task(_run_collect, uf)
    return {"started": True, "uf": uf}


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as exc:
        return {"status": "error", "db": str(exc)}
