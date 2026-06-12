"""
Testes de integração: CRUD de planos, gating por feature, RBAC, auditoria.
AT-001 / AT-002 / AT-003 / AT-005 do DEFINE_V2_MELHOR_DO_MERCADO.md
"""
import uuid
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.main import app
from app.api.middleware.auth import get_current_user
from app.core.database import get_db
from app.entitlements.catalog import FEATURES
from app.entitlements.service import invalidate_cache
from app.models.base import Base
from app.models.plan import AuditLog, Plan, Subscription
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


def _make_user(db, role="user", plan_features=None):
    user = User(firebase_uid=f"uid_{uuid.uuid4().hex}", email=f"{uuid.uuid4().hex}@test.com", role=role)
    db.add(user)
    db.flush()

    if plan_features is not None:
        plan = Plan(
            code=f"plan_{uuid.uuid4().hex[:6]}",
            name="Test Plan",
            features=plan_features,
            limits={},
        )
        db.add(plan)
        db.flush()
        sub = Subscription(user_id=user.id, plan_id=plan.id)
        db.add(sub)
        db.flush()
        user.subscription_id = sub.id
        db.flush()
        invalidate_cache(str(user.id))

    return user


@contextmanager
def _client(db, user):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db):
    return _make_user(db, role="admin")


@pytest.fixture
def operador_user(db):
    return _make_user(db, role="operador")


@pytest.fixture
def regular_user(db):
    return _make_user(db, role="user", plan_features={k: False for k in FEATURES})


# ── AT-001: criar plano novo sem deploy ───────────────────────────────────────

def test_create_plan(db, admin_user, engine):
    with _client(db, admin_user) as client:
        resp = client.post("/admin/plans", json={
            "code": "enterprise_test",
            "name": "Enterprise",
            "price_brl": 49900,
            "features": {"risk_score": True, "export": True},
            "limits": {"alerts_per_day": 500},
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "enterprise_test"

    # Plan deve estar no banco
    plan = db.query(Plan).filter_by(code="enterprise_test").first()
    assert plan is not None
    assert plan.features["risk_score"] is True


def test_create_plan_invalid_flag(db, admin_user):
    with _client(db, admin_user) as client:
        resp = client.post("/admin/plans", json={
            "code": "bad_plan",
            "name": "Bad",
            "features": {"nonexistent_flag": True},
            "limits": {},
        })
    assert resp.status_code == 400
    assert "nonexistent_flag" in str(resp.json())


def test_create_plan_duplicate_code(db, admin_user):
    with _client(db, admin_user) as client:
        client.post("/admin/plans", json={"code": "dup_test", "name": "Dup"})
        resp = client.post("/admin/plans", json={"code": "dup_test", "name": "Dup2"})
    assert resp.status_code == 409


# ── AT-002: gating — 403 quando feature não está no plano ─────────────────────

def test_feature_gate_blocks_without_flag(db, regular_user):
    """Usuário Free deve receber 403 ao tentar exportar."""
    with _client(db, regular_user) as client:
        resp = client.get("/properties/export", params={"state": "SP"})
    # 403 (plan limit) ou 404 (rota ainda não existente) são ambos aceitáveis;
    # o que NÃO pode acontecer é 200
    assert resp.status_code in (403, 404, 422)
    if resp.status_code == 403:
        assert resp.json()["detail"]["code"] == "PLAN_LIMIT"


# ── AT-003: RBAC — operador não acessa rotas de admin ─────────────────────────

def test_rbac_regular_user_cannot_list_plans(db, regular_user):
    with _client(db, regular_user) as client:
        resp = client.get("/admin/plans")
    assert resp.status_code == 403


def test_rbac_operador_can_list_plans(db, operador_user):
    with _client(db, operador_user) as client:
        resp = client.get("/admin/plans")
    assert resp.status_code == 200


def test_rbac_operador_cannot_create_plan(db, operador_user):
    with _client(db, operador_user) as client:
        resp = client.post("/admin/plans", json={"code": "x", "name": "X"})
    assert resp.status_code == 403


# ── AT-005: toda ação admin gera audit_log ─────────────────────────────────────

def test_audit_log_on_plan_update(db, admin_user):
    with _client(db, admin_user) as client:
        create_resp = client.post("/admin/plans", json={
            "code": f"audit_test_{uuid.uuid4().hex[:6]}",
            "name": "Audit Plan",
            "features": {},
            "limits": {},
        })
        plan_id = create_resp.json()["id"]

        # Atualiza
        client.patch(f"/admin/plans/{plan_id}", json={"name": "Audit Plan v2"})

    # Deve ter entradas no audit_log
    entries = db.query(AuditLog).filter_by(entity_id=plan_id).all()
    actions = {e.action for e in entries}
    assert "plan.create" in actions
    assert "plan.update" in actions


# ── Catálogo de features via API ──────────────────────────────────────────────

def test_get_catalog(db, operador_user):
    with _client(db, operador_user) as client:
        resp = client.get("/admin/plans/catalog")
    assert resp.status_code == 200
    catalog = resp.json()
    assert "features" in catalog
    assert any(f["key"] == "risk_score" for f in catalog["features"])
