import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.middleware.auth import get_current_user, require_role
from app.core.database import get_db
from app.entitlements.audit import audit
from app.entitlements.catalog import validate_plan_config
from app.entitlements.service import invalidate_cache
from app.models.plan import Plan
from app.models.user import User

router = APIRouter(prefix="/admin/plans", tags=["admin-plans"])


class PlanCreate(BaseModel):
    code: str
    name: str
    price_brl: int = 0
    features: dict = {}
    limits: dict = {}


class PlanUpdate(BaseModel):
    name: str | None = None
    price_brl: int | None = None
    features: dict | None = None
    limits: dict | None = None
    active: bool | None = None


@router.get("")
def list_plans(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("operador")),
):
    return [
        {
            "id": str(p.id),
            "code": p.code,
            "name": p.name,
            "price_brl": p.price_brl,
            "features": p.features,
            "limits": p.limits,
            "active": p.active,
        }
        for p in db.query(Plan).order_by(Plan.price_brl).all()
    ]


@router.post("", status_code=201)
def create_plan(
    body: PlanCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role("admin")),
):
    errors = validate_plan_config(body.features, body.limits)
    if errors:
        raise HTTPException(400, detail={"errors": errors})
    if db.query(Plan).filter_by(code=body.code).first():
        raise HTTPException(409, detail="Código de plano já existe")

    plan = Plan(
        code=body.code,
        name=body.name,
        price_brl=body.price_brl,
        features=body.features,
        limits=body.limits,
    )
    db.add(plan)
    db.flush()
    audit(db, actor, "plan.create", "plan", str(plan.id), before=None, after=body.model_dump())
    db.commit()
    return {"id": str(plan.id), "code": plan.code}


@router.patch("/{plan_id}")
def update_plan(
    plan_id: uuid.UUID,
    body: PlanUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role("admin")),
):
    plan = db.query(Plan).filter_by(id=plan_id).first()
    if not plan:
        raise HTTPException(404, detail="Plano não encontrado")

    before = {"name": plan.name, "price_brl": plan.price_brl,
               "features": plan.features, "limits": plan.limits, "active": plan.active}

    if body.features is not None:
        errors = validate_plan_config(body.features, body.limits or plan.limits)
        if errors:
            raise HTTPException(400, detail={"errors": errors})
        plan.features = body.features
    if body.limits is not None:
        errors = validate_plan_config(body.features or plan.features, body.limits)
        if errors:
            raise HTTPException(400, detail={"errors": errors})
        plan.limits = body.limits
    if body.name is not None:
        plan.name = body.name
    if body.price_brl is not None:
        plan.price_brl = body.price_brl
    if body.active is not None:
        plan.active = body.active

    after = {"name": plan.name, "price_brl": plan.price_brl,
              "features": plan.features, "limits": plan.limits, "active": plan.active}
    audit(db, actor, "plan.update", "plan", str(plan.id), before=before, after=after)
    db.commit()

    # Invalidate cache for all users on this plan (best-effort — cache expires in 60s anyway)
    return {"id": str(plan.id), "code": plan.code}


@router.get("/catalog")
def get_catalog(
    _: User = Depends(require_role("operador")),
):
    from app.entitlements.catalog import FEATURES, QUOTAS
    return {
        "features": [{"key": f.key, "description": f.description} for f in FEATURES.values()],
        "quotas": [{"key": q.key, "period": q.period, "description": q.description}
                   for q in QUOTAS.values()],
    }
