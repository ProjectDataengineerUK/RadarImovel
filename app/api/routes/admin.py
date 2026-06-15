import json
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.middleware.auth import get_current_user, require_role
from app.core.config import get_settings
from app.core.database import get_db
from app.models.document import Document
from app.models.property import Property
from app.models.user import Alert, User

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()


@router.post("/bootstrap-admin")
def bootstrap_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Promoção do primeiro admin. Só funciona enquanto não há nenhum admin no sistema."""
    admin_count = db.query(User).filter_by(role="admin").count()
    if admin_count > 0:
        raise HTTPException(403, detail="Já existe um admin. Use /admin/users/{id}/role para alterar papéis.")
    current_user.role = "admin"
    db.commit()
    return {"ok": True, "promoted_to": "admin", "user_id": str(current_user.id)}

VALID_UFS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
}


@router.get("/status")
def collector_status(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("operador")),
):
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
    _: User = Depends(require_role("operador")),
):
    uf = req.uf.upper()
    if uf not in VALID_UFS:
        raise HTTPException(status_code=400, detail=f"UF inválida: {uf}")

    background_tasks.add_task(_run_collect, uf)
    return {"started": True, "uf": uf}


@router.post("/reprocess-edital/{property_id}")
def reprocess_edital(
    property_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("operador")),
):
    """Re-extração manual do edital: reseta o Document e republica em edital-events."""
    from google.cloud import pubsub_v1

    prop = db.query(Property).filter_by(id=property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if not prop.edital_url:
        raise HTTPException(status_code=400, detail="Property sem edital_url")

    doc = (
        db.query(Document)
        .filter_by(property_id=property_id, document_type="edital")
        .first()
    )
    if doc:
        doc.processing_status = "pending"
        doc.processing_error = None
        db.commit()

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(
        settings.pubsub_project_id, settings.pubsub_topic_editais
    )
    event = {
        "property_id": str(prop.id),
        "edital_url": prop.edital_url,
        "bank_id": str(prop.bank_id),
    }
    publisher.publish(topic_path, json.dumps(event).encode())

    return {"reprocessing": True, "property_id": str(prop.id)}


@router.get("/health")
def health_check(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("operador")),
):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as exc:
        return {"status": "error", "db": str(exc)}


def _run_geocode_batch(batch: int, delay_ms: int) -> None:
    """Background geocoding: populates lat/lng for properties that lack it."""
    import asyncio
    import time
    import structlog
    from app.core.database import SessionLocal
    from app.services.geocoding import _geocode_nominatim, cep_to_latlong

    log = structlog.get_logger()
    geocoded = 0
    failed = 0

    with SessionLocal() as session:
        props = (
            session.query(Property)
            .filter(Property.latitude.is_(None))
            .order_by(Property.first_seen_at.desc())
            .limit(batch)
            .all()
        )
        log.info("admin.geocode_batch.start", count=len(props))

        for prop in props:
            coords = None
            if prop.zipcode:
                try:
                    coords = asyncio.run(cep_to_latlong(prop.zipcode))
                except Exception:
                    pass
            if not coords and prop.city and prop.state:
                try:
                    coords = asyncio.run(_geocode_nominatim(f"{prop.city}, {prop.state}, Brasil"))
                except Exception:
                    pass

            if coords:
                prop.latitude, prop.longitude = coords
                geocoded += 1
            else:
                failed += 1

            time.sleep(delay_ms / 1000)

        session.commit()

    log.info("admin.geocode_batch.done", geocoded=geocoded, failed=failed)


@router.post("/geocode-batch")
def geocode_batch(
    background_tasks: BackgroundTasks,
    batch: int = 200,
    delay_ms: int = 1100,
    _: User = Depends(require_role("operador")),
):
    """Geocodifica em background propriedades sem lat/lng (Nominatim 1 req/s)."""
    background_tasks.add_task(_run_geocode_batch, batch, delay_ms)
    return {"started": True, "batch": batch, "delay_ms": delay_ms}
