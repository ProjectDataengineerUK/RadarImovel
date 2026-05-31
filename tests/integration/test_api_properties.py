import uuid
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.main import app
from app.core.database import get_db
from app.models.base import Base
from app.models.bank import Bank
from app.models.property import Property


@pytest.fixture(scope="module")
def test_engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def test_session(test_engine):
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(test_session):
    app.dependency_overrides[get_db] = lambda: test_session
    with patch("app.api.middleware.auth.firebase_auth") as mock_auth:
        mock_auth.verify_id_token.return_value = {"uid": "test-uid", "email": "test@test.com"}
        yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_db(test_session):
    bank = Bank(id=uuid.uuid4(), code="caixa", name="Caixa Econômica Federal")
    test_session.add(bank)

    props = [
        Property(
            id=uuid.uuid4(),
            bank_id=bank.id,
            external_code=f"EXT{i}",
            property_type="Apartamento",
            city=city,
            state=state,
            minimum_value=Decimal("100000"),
            current_value=Decimal(str(price)),
            discount_percent=Decimal(str(discount)),
            occupancy_status=occ,
            sale_modality="Licitação Aberta",
            official_url=f"https://example.com/{i}",
            status="active",
            content_hash=f"hash{i}" + "0" * 58,
            opportunity_score=score,
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
        for i, (city, state, price, discount, occ, score) in enumerate([
            ("Goiânia", "GO", 200000, 25, "Desocupado", 65),
            ("São Paulo", "SP", 350000, 10, "Ocupado", 10),
            ("Brasília", "DF", 150000, 40, "Desocupado", 80),
        ])
    ]
    test_session.add_all(props)
    test_session.commit()
    yield
    test_session.query(Property).delete()
    test_session.query(Bank).delete()
    test_session.commit()


def test_list_returns_all_active(client, seeded_db):
    r = client.get("/properties/")
    assert r.status_code == 200
    assert r.json()["total"] == 3


def test_filter_by_state(client, seeded_db):
    r = client.get("/properties/?state=SP")
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["state"] == "SP"


def test_filter_by_max_price(client, seeded_db):
    r = client.get("/properties/?max_price=200000")
    assert r.status_code == 200
    assert all(i["current_value"] <= 200000 for i in r.json()["items"])


def test_filter_by_min_discount(client, seeded_db):
    r = client.get("/properties/?min_discount=30")
    assert r.status_code == 200
    assert r.json()["total"] == 1


def test_filter_by_occupancy(client, seeded_db):
    r = client.get("/properties/?occupancy_status=Desocupado")
    assert r.status_code == 200
    assert all(i["occupancy_status"] == "Desocupado" for i in r.json()["items"])


def test_ordered_by_score_desc(client, seeded_db):
    r = client.get("/properties/")
    scores = [i["opportunity_score"] for i in r.json()["items"]]
    assert scores == sorted(scores, reverse=True)


def test_get_property_not_found(client, seeded_db):
    r = client.get(f"/properties/{uuid.uuid4()}")
    assert r.status_code == 404


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
