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

    # Saúde dos coletores — todas as 16 fontes ativas (bancos + leiloeiros + judicial)
    connector_health = db.execute(text("""
        SELECT
            b.code,
            b.name,
            b.source_type,
            b.tos_compliant,
            MAX(p.last_seen_at)       AS last_seen,
            COUNT(p.id)               AS property_count
        FROM banks b
        LEFT JOIN properties p ON p.bank_id = b.id
        WHERE b.active = true
        GROUP BY b.code, b.name, b.source_type, b.tos_compliant
        ORDER BY b.source_type, b.name
    """)).fetchall()

    # Alertas com status = sent/failed hoje (para taxa de entrega)
    alerts_sent = (
        db.query(func.count(Alert.id))
        .filter(Alert.status == "sent", func.date(Alert.created_at) == func.current_date())
        .scalar()
    )
    alerts_failed = (
        db.query(func.count(Alert.id))
        .filter(Alert.status == "failed", func.date(Alert.created_at) == func.current_date())
        .scalar()
    )

    return {
        "users_by_plan": [
            {"plan_code": r.code, "plan_name": r.name, "count": r.count}
            for r in users_by_plan
        ],
        "alerts_today": alerts_today or 0,
        "alerts_suppressed_today": alerts_suppressed or 0,
        "alerts_sent_today": alerts_sent or 0,
        "alerts_failed_today": alerts_failed or 0,
        "connector_health": [
            {
                "bank_code": r.code,
                "bank_name": r.name,
                "source_type": r.source_type,
                "tos_compliant": r.tos_compliant,
                "last_seen_at": r.last_seen,
                "property_count": r.property_count,
            }
            for r in connector_health
        ],
    }
