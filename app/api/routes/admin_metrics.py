from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.middleware.auth import require_role
from app.core.database import get_db
from app.models.plan import Plan, Subscription
from app.models.user import Alert, User

router = APIRouter(prefix="/admin/metrics", tags=["admin-metrics"])


@router.get("")
def get_metrics(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("operador")),
):
    # Usuários por plano
    users_by_plan = (
        db.query(Plan.code, Plan.name, func.count(User.id).label("count"))
        .outerjoin(Subscription, Subscription.plan_id == Plan.id)
        .outerjoin(User, User.subscription_id == Subscription.id)
        .group_by(Plan.code, Plan.name)
        .all()
    )

    # Alertas enviados hoje
    alerts_today = (
        db.query(func.count(Alert.id))
        .filter(func.date(Alert.created_at) == func.current_date())
        .scalar()
    )

    # Alertas suprimidos hoje (status = suppressed)
    alerts_suppressed = (
        db.query(func.count(Alert.id))
        .filter(
            Alert.status == "suppressed",
            func.date(Alert.created_at) == func.current_date(),
        )
        .scalar()
    )

    # Saúde dos coletores (última coleta por banco)
    connector_health = db.execute(text("""
        SELECT b.code, b.name, MAX(p.last_seen_at) AS last_seen
        FROM banks b
        LEFT JOIN properties p ON p.bank_id = b.id
        WHERE b.active = true
        GROUP BY b.code, b.name
        ORDER BY b.name
    """)).fetchall()

    return {
        "users_by_plan": [
            {"plan_code": r.code, "plan_name": r.name, "count": r.count}
            for r in users_by_plan
        ],
        "alerts_today": alerts_today or 0,
        "alerts_suppressed_today": alerts_suppressed or 0,
        "connector_health": [
            {"bank_code": r.code, "bank_name": r.name, "last_seen_at": r.last_seen}
            for r in connector_health
        ],
    }
