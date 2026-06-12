"""Job diário: rebaixa assinaturas expiradas para o plano Free."""
import sys
import structlog
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.entitlements.service import invalidate_cache
from app.models.plan import Plan, Subscription
from app.models.user import User

log = configure_logging("expire_subscriptions")


def run() -> None:
    db = SessionLocal()
    try:
        free_plan = db.query(Plan).filter_by(code="free", active=True).first()
        if not free_plan:
            log.error("expire_subscriptions.no_free_plan")
            sys.exit(1)

        now = datetime.now(timezone.utc)
        expired = (
            db.query(Subscription)
            .filter(Subscription.expires_at != None, Subscription.expires_at < now)  # noqa: E711
            .all()
        )
        degraded = 0
        for sub in expired:
            user = db.query(User).filter_by(subscription_id=sub.id).first()
            if not user:
                continue

            new_sub = Subscription(
                user_id=user.id,
                plan_id=free_plan.id,
                expires_at=None,
            )
            db.add(new_sub)
            db.flush()
            user.subscription_id = new_sub.id
            invalidate_cache(str(user.id))
            degraded += 1
            log.info("expire_subscriptions.downgraded", user_id=str(user.id))

        db.commit()
        log.info("expire_subscriptions.done", downgraded=degraded)
    finally:
        db.close()


if __name__ == "__main__":
    run()
