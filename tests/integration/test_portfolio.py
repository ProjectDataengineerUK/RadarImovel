"""Testes de integração: CRUD carteira Kanban.
AT-008 do DEFINE_V2_MELHOR_DO_MERCADO.md
"""
import uuid
from contextlib import contextmanager
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.main import app
from app.api.middleware.auth import get_current_user
from app.core.database import get_db
from app.entitlements.service import invalidate_cache
from app.models.base import Base
from app.models.bank import Bank
from app.models.plan import Plan, Subscription
from app.models.portfolio import PortfolioItem
from app.models.property import Property
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


def _make_bank(db):
    bank = Bank(code=f"bk_{uuid.uuid4().hex[:4]}", name="Test Bank", active=True)
    db.add(bank)
    db.flush()
    return bank


def _make_property(db, bank):
    prop = Property(
        bank_id=bank.id,
        external_code=f"ext_{uuid.uuid4().hex[:6]}",
        property_type="apartamento",
        city="São Paulo",
        state="SP",
        current_value=Decimal("150000.00"),
        minimum_value=Decimal("120000.00"),
        occupancy_status="livre",
        sale_modality="leilão SFI",
        official_url=f"https://example.com/{uuid.uuid4().hex[:8]}",
        status="active",
        content_hash="a" * 64,
    )
    db.add(prop)
    db.flush()
    return prop


def _make_user(db, role="user", with_portfolio=True):
    plan = Plan(
        code=f"plan_{uuid.uuid4().hex[:6]}",
        name="Pro",
        features={"portfolio": True} if with_portfolio else {"portfolio": False},
        limits={},
    )
    db.add(plan)
    db.flush()
    user = User(
        firebase_uid=f"uid_{uuid.uuid4().hex}",
        email=f"{uuid.uuid4().hex[:6]}@test.com",
        role=role,
    )
    db.add(user)
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


# ── AT-008: CRUD carteira ──────────────────────────────────────────────────────

def test_add_to_portfolio(db):
    bank = _make_bank(db)
    prop = _make_property(db, bank)
    user = _make_user(db, with_portfolio=True)

    with _client(db, user) as client:
        resp = client.post("/portfolio", json={
            "property_id": str(prop.id),
            "stage": "monitorando",
            "notes": "Analisar depois",
        })

    assert resp.status_code == 201
    data = resp.json()
    assert data["stage"] == "monitorando"
    assert data["property_id"] == str(prop.id)


def test_add_duplicate_returns_409(db):
    bank = _make_bank(db)
    prop = _make_property(db, bank)
    user = _make_user(db, with_portfolio=True)

    with _client(db, user) as client:
        client.post("/portfolio", json={"property_id": str(prop.id), "stage": "monitorando"})
        resp = client.post("/portfolio", json={"property_id": str(prop.id), "stage": "analisando"})

    assert resp.status_code == 409


def test_list_portfolio(db):
    bank = _make_bank(db)
    prop = _make_property(db, bank)
    user = _make_user(db, with_portfolio=True)

    with _client(db, user) as client:
        client.post("/portfolio", json={"property_id": str(prop.id)})
        resp = client.get("/portfolio")

    assert resp.status_code == 200
    assert len(resp.json()["items"]) >= 1


def test_update_stage(db):
    bank = _make_bank(db)
    prop = _make_property(db, bank)
    user = _make_user(db, with_portfolio=True)

    with _client(db, user) as client:
        add_resp = client.post("/portfolio", json={"property_id": str(prop.id), "stage": "monitorando"})
        item_id = add_resp.json()["id"]

        patch_resp = client.patch(f"/portfolio/{item_id}", json={"stage": "analisando"})

    assert patch_resp.status_code == 200
    assert patch_resp.json()["stage"] == "analisando"


def test_update_with_actual_price(db):
    bank = _make_bank(db)
    prop = _make_property(db, bank)
    user = _make_user(db, with_portfolio=True)

    with _client(db, user) as client:
        add_resp = client.post("/portfolio", json={"property_id": str(prop.id)})
        item_id = add_resp.json()["id"]

        patch_resp = client.patch(f"/portfolio/{item_id}", json={
            "stage": "arrematado",
            "actual_purchase_price": 145000,
            "notes": "Comprado na 2ª praça",
        })

    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["stage"] == "arrematado"
    assert data["notes"] == "Comprado na 2ª praça"


def test_delete_portfolio_item(db):
    bank = _make_bank(db)
    prop = _make_property(db, bank)
    user = _make_user(db, with_portfolio=True)

    with _client(db, user) as client:
        add_resp = client.post("/portfolio", json={"property_id": str(prop.id)})
        item_id = add_resp.json()["id"]

        del_resp = client.delete(f"/portfolio/{item_id}")
        assert del_resp.status_code == 204

        list_resp = client.get("/portfolio")
        ids = [i["id"] for i in list_resp.json()["items"]]
        assert item_id not in ids


def test_portfolio_requires_feature(db):
    bank = _make_bank(db)
    prop = _make_property(db, bank)
    user = _make_user(db, with_portfolio=False)

    with _client(db, user) as client:
        resp = client.post("/portfolio", json={"property_id": str(prop.id)})

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PLAN_LIMIT"


def test_user_cannot_see_other_users_items(db):
    bank = _make_bank(db)
    prop = _make_property(db, bank)
    user_a = _make_user(db, with_portfolio=True)
    user_b = _make_user(db, with_portfolio=True)

    with _client(db, user_a) as client:
        add_resp = client.post("/portfolio", json={"property_id": str(prop.id)})
        item_id = add_resp.json()["id"]

    with _client(db, user_b) as client:
        resp = client.patch(f"/portfolio/{item_id}", json={"stage": "analisando"})

    assert resp.status_code == 404


def test_invalid_stage_returns_422(db):
    bank = _make_bank(db)
    prop = _make_property(db, bank)
    user = _make_user(db, with_portfolio=True)

    with _client(db, user) as client:
        resp = client.post("/portfolio", json={
            "property_id": str(prop.id),
            "stage": "invalido",
        })

    assert resp.status_code == 422
