import stripe
import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.middleware.auth import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.entitlements.service import invalidate_cache
from app.models.plan import Plan, Subscription
from app.models.user import User

logger = structlog.get_logger()
router = APIRouter(prefix="/billing", tags=["billing"])
plans_router = APIRouter(prefix="/plans", tags=["plans"])


def _stripe_client() -> stripe.StripeClient:
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(503, detail="Pagamentos não configurados")
    return stripe.StripeClient(settings.stripe_secret_key)


class CheckoutRequest(BaseModel):
    plan_code: str
    billing: str = "monthly"  # "monthly" | "annual"


@plans_router.get("")
def list_plans_public(db: Session = Depends(get_db)):
    from app.entitlements.catalog import FEATURES, QUOTAS
    plans = db.query(Plan).filter_by(active=True).order_by(Plan.sort_order, Plan.price_brl).all()
    return {
        "plans": [
            {
                "id": str(p.id),
                "code": p.code,
                "name": p.name,
                "description": p.description,
                "price_brl": p.price_brl,
                "discount_brl": p.discount_brl,
                "stripe_price_id_monthly": p.stripe_price_id_monthly,
                "stripe_price_id_annual": p.stripe_price_id_annual,
                "sort_order": p.sort_order,
                "features": p.features,
                "limits": p.limits,
            }
            for p in plans
        ],
        "features": [{"key": f.key, "description": f.description} for f in FEATURES.values()],
        "quotas": [{"key": q.key, "period": q.period, "description": q.description} for q in QUOTAS.values()],
    }


@router.post("/checkout")
def create_checkout_session(
    body: CheckoutRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    client = _stripe_client()

    plan = db.query(Plan).filter_by(code=body.plan_code, active=True).first()
    if not plan:
        raise HTTPException(404, detail="Plano não encontrado")

    price_id = plan.stripe_price_id_annual if body.billing == "annual" else plan.stripe_price_id_monthly
    if not price_id:
        raise HTTPException(400, detail=f"Plano '{body.plan_code}' sem price Stripe configurado")

    # Cria ou recupera customer Stripe
    if user.stripe_customer_id:
        customer_id = user.stripe_customer_id
    else:
        customer = client.customers.create(params={"email": user.email, "metadata": {"user_id": str(user.id)}})
        customer_id = customer.id
        user.stripe_customer_id = customer_id
        db.commit()

    session = client.checkout.sessions.create(params={
        "customer": customer_id,
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": settings.stripe_success_url + "&plan=" + body.plan_code,
        "cancel_url": settings.stripe_cancel_url,
        "metadata": {"user_id": str(user.id), "plan_code": body.plan_code},
        "allow_promotion_codes": True,
        "subscription_data": {"metadata": {"user_id": str(user.id), "plan_code": body.plan_code}},
    })
    return {"url": session.url}


@router.post("/portal")
def create_portal_session(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _stripe_client()
    settings = get_settings()

    if not user.stripe_customer_id:
        raise HTTPException(400, detail="Nenhuma assinatura ativa encontrada")

    session = client.billing_portal.sessions.create(params={
        "customer": user.stripe_customer_id,
        "return_url": settings.stripe_cancel_url.replace("?checkout=cancelled", "/configuracoes"),
    })
    return {"url": session.url}


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise HTTPException(503, detail="Webhook não configurado")

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, settings.stripe_webhook_secret)
    except stripe.SignatureVerificationError:
        raise HTTPException(400, detail="Assinatura inválida")

    if event["type"] in ("invoice.paid", "customer.subscription.updated"):
        _handle_subscription_active(event["data"]["object"], db)
    elif event["type"] == "customer.subscription.deleted":
        _handle_subscription_cancelled(event["data"]["object"], db)

    return {"received": True}


def _handle_subscription_active(obj: dict, db: Session) -> None:
    customer_id = obj.get("customer")
    stripe_sub_id = obj.get("id") or obj.get("subscription")
    plan_code = (obj.get("metadata") or {}).get("plan_code")

    user = db.query(User).filter_by(stripe_customer_id=customer_id).first()
    if not user:
        logger.warning("stripe_webhook.user_not_found", customer_id=customer_id)
        return

    plan = db.query(Plan).filter_by(code=plan_code, active=True).first() if plan_code else None
    if not plan:
        logger.warning("stripe_webhook.plan_not_found", plan_code=plan_code)
        return

    if stripe_sub_id:
        user.stripe_subscription_id = stripe_sub_id

    sub = Subscription(user_id=user.id, plan_id=plan.id, expires_at=None, created_by=None)
    db.add(sub)
    db.flush()
    user.subscription_id = sub.id
    db.commit()
    invalidate_cache(str(user.id))
    logger.info("stripe_webhook.subscription_activated", user_id=str(user.id), plan=plan_code)


def _handle_subscription_cancelled(obj: dict, db: Session) -> None:
    customer_id = obj.get("customer")
    user = db.query(User).filter_by(stripe_customer_id=customer_id).first()
    if not user:
        return

    free_plan = db.query(Plan).filter_by(code="free", active=True).first()
    if not free_plan:
        return

    sub = Subscription(user_id=user.id, plan_id=free_plan.id, expires_at=None, created_by=None)
    db.add(sub)
    db.flush()
    user.subscription_id = sub.id
    user.stripe_subscription_id = None
    db.commit()
    invalidate_cache(str(user.id))
    logger.info("stripe_webhook.subscription_cancelled", user_id=str(user.id))
