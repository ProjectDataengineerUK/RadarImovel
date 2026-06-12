import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.middleware.auth import get_current_user, require_role
from app.core.database import get_db
from app.entitlements.audit import audit
from app.entitlements.service import invalidate_cache
from app.models.plan import Plan, Subscription
from app.models.user import User, USER_ROLES

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def _mask_email(email: str, role: str) -> str:
    """Mascara e-mail para papel suporte; admin vê completo."""
    if role == "admin":
        return email
    parts = email.split("@")
    if len(parts) != 2:
        return "***"
    local = parts[0]
    return f"{local[:2]}***@{parts[1]}"


@router.get("")
def list_users(
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role("suporte")),
):
    total = db.query(User).count()
    users = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(min(limit, 200)).all()
    return {
        "total": total,
        "items": [_user_summary(u, actor.role) for u in users],
    }


@router.get("/{user_id}")
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role("suporte")),
):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(404, detail="Usuário não encontrado")
    return _user_summary(user, actor.role)


class AssignPlanRequest(BaseModel):
    plan_code: str
    expires_at: datetime | None = None


@router.post("/{user_id}/plan")
def assign_plan(
    user_id: uuid.UUID,
    body: AssignPlanRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role("operador")),
):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(404, detail="Usuário não encontrado")

    plan = db.query(Plan).filter_by(code=body.plan_code, active=True).first()
    if not plan:
        raise HTTPException(404, detail=f"Plano '{body.plan_code}' não encontrado ou inativo")

    before = {"plan_code": _current_plan_code(db, user), "expires_at": None}

    sub = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        expires_at=body.expires_at,
        created_by=actor.id,
    )
    db.add(sub)
    db.flush()
    user.subscription_id = sub.id
    db.flush()

    after = {"plan_code": body.plan_code, "expires_at": body.expires_at.isoformat() if body.expires_at else None}
    audit(db, actor, "user.assign_plan", "user", str(user.id), before=before, after=after)
    db.commit()
    invalidate_cache(str(user.id))
    return {"ok": True, "plan": body.plan_code}


class SetRoleRequest(BaseModel):
    role: str


@router.post("/{user_id}/role")
def set_role(
    user_id: uuid.UUID,
    body: SetRoleRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role("admin")),
):
    if body.role not in USER_ROLES:
        raise HTTPException(400, detail=f"Papel inválido. Válidos: {USER_ROLES}")

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(404, detail="Usuário não encontrado")
    if str(user.id) == str(actor.id):
        raise HTTPException(400, detail="Não é possível alterar o próprio papel")

    before = {"role": user.role}
    user.role = body.role
    after = {"role": body.role}
    audit(db, actor, "user.set_role", "user", str(user.id), before=before, after=after)
    db.commit()
    invalidate_cache(str(user.id))
    return {"ok": True, "role": body.role}


def _user_summary(user: User, actor_role: str) -> dict:
    plan_code = None
    if user.subscription and user.subscription.plan:
        plan_code = user.subscription.plan.code

    return {
        "id": str(user.id),
        "email": _mask_email(user.email, actor_role),
        "role": user.role,
        "plan": plan_code or "free",
        "telegram_connected": user.telegram_chat_id is not None,
        "created_at": user.created_at.isoformat(),
    }


def _current_plan_code(db: Session, user: User) -> str | None:
    if not user.subscription_id:
        return None
    sub = db.query(Subscription).filter_by(id=user.subscription_id).first()
    if not sub:
        return None
    plan = db.query(Plan).filter_by(id=sub.plan_id).first()
    return plan.code if plan else None
