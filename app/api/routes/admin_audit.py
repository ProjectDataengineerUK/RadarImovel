from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.middleware.auth import require_role
from app.core.database import get_db
from app.models.plan import AuditLog
from app.models.user import User

router = APIRouter(prefix="/admin/audit", tags=["admin-audit"])


@router.get("")
def list_audit_log(
    entity_type: str | None = None,
    entity_id: str | None = None,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("operador")),
):
    q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)

    total = q.count()
    items = q.offset(offset).limit(min(limit, 200)).all()

    return {
        "total": total,
        "items": [
            {
                "id": str(e.id),
                "actor_user_id": str(e.actor_user_id),
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "before": e.before,
                "after": e.after,
                "created_at": e.created_at.isoformat(),
            }
            for e in items
        ],
    }
