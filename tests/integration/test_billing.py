"""
Testes de integração: billing Stripe — checkout, portal, webhook.
"""
import hashlib
import hmac
import json
import time
import uuid
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.main import app
from app.api.middleware.auth import get_current_user
from app.core.database import get_db
from app.models.base import Base
from app.models.plan import Plan, Subscription
from app.models.user import User


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def _make_user(db, *, role="user", stripe_customer_id=None):
    user = User(
        firebase_uid=f"uid_{uuid.uuid4().hex}",
        email=f"{uuid.uuid4().hex}@test.com",
        role=role,
        stripe_customer_id=stripe_customer_id,
    )
    db.add(user)
    db.flush()
    return user


def _make_plan(db, *, code=None, price_brl=9900, price_id_monthly="price_monthly_abc",
               price_id_annual="price_annual_abc"):
    plan = Plan(
        code=code or f"plan_{uuid.uuid4().hex[:6]}",
        name="Test Pro",
        price_brl=price_brl,
        stripe_price_id_monthly=price_id_monthly,
        stripe_price_id_annual=price_id_annual,
        features={"risk_score": True},
        limits={"alerts_per_day": 50},
    )
    db.add(plan)
    db.flush()
    return plan


@contextmanager
def _client(db, user=None):
    app.dependency_overrides[get_db] = lambda: db
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ── GET /plans — endpoint público ────────────────────────────────────────────

def test_plans_public_no_auth(db):
    _make_plan(db, code=f"pro_{uuid.uuid4().hex[:4]}")
    with _client(db) as client:
        resp = client.get("/plans")
    assert resp.status_code == 200
    data = resp.json()
    assert "plans" in data
    assert "features" in data
    assert "quotas" in data


def test_plans_public_returns_active_only(db):
    active = _make_plan(db, code=f"active_{uuid.uuid4().hex[:4]}")
    inactive = _make_plan(db, code=f"inactive_{uuid.uuid4().hex[:4]}")
    inactive.active = False
    db.flush()

    with _client(db) as client:
        resp = client.get("/plans")

    codes = [p["code"] for p in resp.json()["plans"]]
    assert active.code in codes
    assert inactive.code not in codes


# ── POST /billing/checkout ────────────────────────────────────────────────────

def _fake_settings(**overrides):
    s = MagicMock()
    s.stripe_secret_key = overrides.get("stripe_secret_key", "sk_test_fake")
    s.stripe_webhook_secret = overrides.get("stripe_webhook_secret", "whsec_fake")
    s.stripe_success_url = overrides.get("stripe_success_url", "https://example.com/planos?checkout=success")
    s.stripe_cancel_url = overrides.get("stripe_cancel_url", "https://example.com/planos?checkout=cancelled")
    return s


def test_checkout_creates_session(db):
    user = _make_user(db)
    plan = _make_plan(db, code=f"pro_{uuid.uuid4().hex[:4]}")

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/pay/cs_test_abc"

    mock_customer = MagicMock()
    mock_customer.id = "cus_new123"

    with patch("app.api.routes.billing.stripe.StripeClient") as MockClient, \
         patch("app.api.routes.billing.get_settings", return_value=_fake_settings()):
        instance = MockClient.return_value
        instance.customers.create.return_value = mock_customer
        instance.checkout.sessions.create.return_value = mock_session

        with _client(db, user) as client:
            resp = client.post("/billing/checkout", json={"plan_code": plan.code, "billing": "monthly"})

    assert resp.status_code == 200
    assert resp.json()["url"] == "https://checkout.stripe.com/pay/cs_test_abc"


def test_checkout_unknown_plan_returns_404(db):
    user = _make_user(db)
    with patch("app.api.routes.billing.stripe.StripeClient"), \
         patch("app.api.routes.billing.get_settings", return_value=_fake_settings()):
        with _client(db, user) as client:
            resp = client.post("/billing/checkout", json={"plan_code": "nonexistent", "billing": "monthly"})
    assert resp.status_code == 404


def test_checkout_reuses_existing_customer(db):
    user = _make_user(db, stripe_customer_id="cus_existing456")
    plan = _make_plan(db, code=f"pro_{uuid.uuid4().hex[:4]}")

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/pay/cs_test_xyz"

    with patch("app.api.routes.billing.stripe.StripeClient") as MockClient, \
         patch("app.api.routes.billing.get_settings", return_value=_fake_settings()):
        instance = MockClient.return_value
        instance.checkout.sessions.create.return_value = mock_session

        with _client(db, user) as client:
            client.post("/billing/checkout", json={"plan_code": plan.code, "billing": "monthly"})

        # Não deve criar novo customer quando já existe
        instance.customers.create.assert_not_called()


# ── POST /billing/webhook ─────────────────────────────────────────────────────

def _make_webhook_payload(event_type: str, obj: dict, secret: str = "whsec_test") -> tuple[bytes, str]:
    payload = json.dumps({"type": event_type, "data": {"object": obj}}).encode()
    ts = str(int(time.time()))
    signed = f"{ts}.{payload.decode()}"
    sig = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    header = f"t={ts},v1={sig}"
    return payload, header


def test_webhook_subscription_activates_user(db):
    user = _make_user(db, stripe_customer_id="cus_wh_test")
    plan = _make_plan(db, code=f"wh_pro_{uuid.uuid4().hex[:4]}")
    secret = "whsec_fake_secret"

    obj = {
        "id": "sub_abc123",
        "customer": "cus_wh_test",
        "metadata": {"plan_code": plan.code},
    }
    payload, sig_header = _make_webhook_payload("invoice.paid", obj, secret)

    with patch("app.api.routes.billing.stripe.Webhook.construct_event") as mock_construct, \
         patch("app.api.routes.billing.get_settings", return_value=_fake_settings(stripe_webhook_secret=secret)):
        mock_construct.return_value = {"type": "invoice.paid", "data": {"object": obj}}

        with _client(db) as client:
            resp = client.post(
                "/billing/webhook",
                content=payload,
                headers={"stripe-signature": sig_header, "content-type": "application/json"},
            )

    assert resp.status_code == 200
    db.refresh(user)
    assert user.stripe_subscription_id == "sub_abc123"
    assert user.subscription_id is not None


def test_webhook_subscription_cancelled_downgrades_to_free(db):
    free = _make_plan(db, code="free", price_brl=0, price_id_monthly=None, price_id_annual=None)
    user = _make_user(db, stripe_customer_id="cus_cancel_test")
    plan = _make_plan(db, code=f"pro_cancel_{uuid.uuid4().hex[:4]}")
    sub = Subscription(user_id=user.id, plan_id=plan.id)
    db.add(sub)
    db.flush()
    user.subscription_id = sub.id
    user.stripe_subscription_id = "sub_to_cancel"
    db.flush()

    secret = "whsec_fake2"
    obj = {"customer": "cus_cancel_test", "metadata": {}}

    with patch("app.api.routes.billing.stripe.Webhook.construct_event") as mock_construct, \
         patch("app.api.routes.billing.get_settings", return_value=_fake_settings(stripe_webhook_secret=secret)):
        mock_construct.return_value = {
            "type": "customer.subscription.deleted",
            "data": {"object": obj},
        }

        with _client(db) as client:
            resp = client.post(
                "/billing/webhook",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=fake", "content-type": "application/json"},
            )

    assert resp.status_code == 200
    db.refresh(user)
    assert user.stripe_subscription_id is None
    new_sub = db.query(Subscription).filter_by(id=user.subscription_id).first()
    assert new_sub.plan_id == free.id


def test_webhook_invalid_signature_returns_400(db):
    import stripe as stripe_lib
    with patch("app.api.routes.billing.stripe.Webhook.construct_event") as mock_construct, \
         patch("app.api.routes.billing.get_settings", return_value=_fake_settings(stripe_webhook_secret="whsec_real")):
        mock_construct.side_effect = stripe_lib.SignatureVerificationError("bad sig", "t=1,v1=bad")

        with _client(db) as client:
            resp = client.post(
                "/billing/webhook",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=bad", "content-type": "application/json"},
            )
    assert resp.status_code == 400
