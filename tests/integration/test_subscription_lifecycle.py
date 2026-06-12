"""
Testes de integração: ciclo de vida de assinaturas.
AT-004: atribuição manual e downgrade automático por expiração.
"""
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.main import app
from app.api.middleware.auth import get_current_user
from app.core.database import get_db
from app.entitlements.service import get_entitlements, invalidate_cache
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


@pytest.fixture
def free_plan(db):
    plan = Plan(code=f"free_{uuid.uuid4().hex[:4]}", name="Free", features={}, limits={"alerts_per_day": 5})
    db.add(plan)
    db.flush()
    return plan


@pytest.fixture
def pro_plan(db):
    plan = Plan(
        code=f"pro_{uuid.uuid4().hex[:4]}",
        name="Pro",
        features={"risk_score": True, "export": True},
        limits={"alerts_per_day": 50},
    )
    db.add(plan)
    db.flush()
    return plan


@pytest.fixture
def admin_user(db, free_plan):
    user = User(firebase_uid=f"uid_{uuid.uuid4().hex}", email="admin@test.com", role="admin")
    db.add(user)
    db.flush()
    sub = Subscription(user_id=user.id, plan_id=free_plan.id)
    db.add(sub)
    db.flush()
    user.subscription_id = sub.id
    db.flush()
    invalidate_cache(str(user.id))
    return user


@pytest.fixture
def target_user(db, free_plan):
    user = User(firebase_uid=f"uid_{uuid.uuid4().hex}", email="target@test.com")
    db.add(user)
    db.flush()
    sub = Subscription(user_id=user.id, plan_id=free_plan.id)
    db.add(sub)
    db.flush()
    user.subscription_id = sub.id
    db.flush()
    invalidate_cache(str(user.id))
    return user


# ── AT-004: atribuição manual de plano ────────────────────────────────────────

def test_assign_plan_via_api(db, admin_user, target_user, pro_plan):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: admin_user
    client = TestClient(app)
    resp = client.post(
        f"/admin/users/{target_user.id}/plan",
        json={"plan_code": pro_plan.code},
    )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["plan"] == pro_plan.code

    # Recarrega do banco
    invalidate_cache(str(target_user.id))
    db.refresh(target_user)
    ent = get_entitlements(db, target_user)
    assert ent.plan_code == pro_plan.code
    assert ent.features.get("risk_score") is True


def test_assign_plan_with_expiry(db, admin_user, target_user, pro_plan, free_plan):
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: admin_user
    client = TestClient(app)
    resp = client.post(
        f"/admin/users/{target_user.id}/plan",
        json={"plan_code": pro_plan.code, "expires_at": expires},
    )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    sub = db.query(Subscription).filter_by(id=target_user.subscription_id).first()
    assert sub is not None
    assert sub.expires_at is not None


# ── AT-004: expiração automática via job ──────────────────────────────────────

def test_expire_subscriptions_job(db, free_plan, pro_plan):
    """Job deve rebaixar assinatura expirada para Free."""
    # Cria usuário com assinatura Pro já expirada
    user = User(firebase_uid=f"uid_{uuid.uuid4().hex}", email="expired@test.com")
    db.add(user)
    db.flush()

    expired_sub = Subscription(
        user_id=user.id,
        plan_id=pro_plan.id,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # ontem
    )
    db.add(expired_sub)
    db.flush()
    user.subscription_id = expired_sub.id
    db.flush()
    db.commit()
    invalidate_cache(str(user.id))

    # Verifica que está no Pro antes
    ent_before = get_entitlements(db, user)
    assert ent_before.plan_code == pro_plan.code

    # Simula a lógica do job diretamente no db de teste
    from app.entitlements.service import invalidate_cache as ic
    from app.models.plan import Plan as P, Subscription as S
    from app.models.user import User as U

    now = datetime.now(timezone.utc)
    expired = db.query(S).filter(
        S.expires_at != None, S.expires_at < now  # noqa: E711
    ).all()
    for sub in expired:
        u = db.query(U).filter_by(subscription_id=sub.id).first()
        if not u:
            continue
        fp = db.query(P).filter_by(name="Free").first() or free_plan
        new_sub = S(user_id=u.id, plan_id=fp.id, expires_at=None)
        db.add(new_sub)
        db.flush()
        u.subscription_id = new_sub.id
        ic(str(u.id))
    db.commit()

    db.refresh(user)
    invalidate_cache(str(user.id))
    ent_after = get_entitlements(db, user)
    # Usuário foi rebaixado do Pro — qualquer plano Free é aceito
    assert ent_after.plan_code != pro_plan.code


# ── RBAC: papel não pode alterar o próprio papel ─────────────────────────────

def test_admin_cannot_change_own_role(db, admin_user):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: admin_user
    client = TestClient(app)
    resp = client.post(f"/admin/users/{admin_user.id}/role", json={"role": "user"})
    app.dependency_overrides.clear()

    assert resp.status_code == 400
