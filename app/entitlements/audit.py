from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.plan import AuditLog
from app.models.user import User


def audit(
    db: Session,
    actor: User,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict | None = None,
    after: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
    )
    db.add(entry)
    db.flush()
    return entry
