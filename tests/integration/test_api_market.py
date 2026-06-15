"""Integration tests for GET /market/prices and POST /market/properties/{id}/roi."""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.main import app
from app.api.middleware.auth import get_current_user
from app.core.database import get_db
from app.models.base import Base
from app.models.bank import Bank
from app.models.property import MarketPrice, Property
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
def session(engine):
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.rollback()
    s.close()


_MOCK_USER = User(firebase_uid="uid-test", email="t@t.com", role="admin")


@pytest.fixture
def client(session):
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: _MOCK_USER
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def seeded(session):
    bank = Bank(id=uuid.uuid4(), code="caixa", name="Caixa")
    session.add(bank)

    prop = Property(
        id=uuid.uuid4(),
        bank_id=bank.id,
        external_code="MKT001",
        property_type="Apartamento",
        city="São Paulo",
        state="SP",
        minimum_value=Decimal("200000"),
        current_value=Decimal("200000"),
        discount_percent=Decimal("30"),
        occupancy_status="Desocupado",
        sale_modality="Licitação Aberta",
        official_url="https://example.com/mkt001",
        status="active",
        content_hash="a" * 64,
        opportunity_score=75,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    session.add(prop)

    mp = MarketPrice(
        city="São Paulo",
        uf="SP",
        property_type="Apartamento",
        price_per_sqm=Decimal("9500"),
        reference_month=date(2026, 6, 1),
        source="fipezap",
    )
    session.add(mp)
    session.commit()

    yield {"prop_id": str(prop.id)}

    session.query(MarketPrice).delete()
    session.query(Property).delete()
    session.query(Bank).delete()
    session.commit()


def test_get_market_prices_returns_200(client, seeded):
    r = client.get("/market/prices", params={"city": "São Paulo", "uf": "SP"})
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    assert items[0]["city"] == "São Paulo"
    assert items[0]["uf"] == "SP"
    assert items[0]["price_per_sqm"] == 9500.0


def test_get_market_prices_no_filter(client, seeded):
    r = client.get("/market/prices")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_post_roi_revenda(client, seeded):
    prop_id = seeded["prop_id"]
    with (
        patch("app.api.routes.market.get_market_prices_for_city") as mock_mp,
        patch("app.api.routes.market.get_selic_rate_async", new_callable=AsyncMock) as mock_selic,
    ):
        mock_mp.return_value = type("MP", (), {"price_per_sqm_sale": Decimal("9500"), "price_per_sqm_rent": Decimal("45")})()
        mock_selic.return_value = Decimal("0.105")

        r = client.post(
            f"/market/properties/{prop_id}/roi",
            json={"intention": "revenda", "horizon_months": 24, "area_sqm": 70.0, "reform_cost_per_sqm": 500.0},
        )

    assert r.status_code == 200
    body = r.json()
    assert "roi_pct" in body
    assert body["roi_pct"] is not None
    assert body["cdi_equivalent_pct"] > 0


def test_post_roi_aluguel(client, seeded):
    prop_id = seeded["prop_id"]
    with (
        patch("app.api.routes.market.get_market_prices_for_city") as mock_mp,
        patch("app.api.routes.market.get_selic_rate_async", new_callable=AsyncMock) as mock_selic,
    ):
        mock_mp.return_value = type("MP", (), {"price_per_sqm_sale": Decimal("9500"), "price_per_sqm_rent": Decimal("45")})()
        mock_selic.return_value = Decimal("0.105")

        r = client.post(
            f"/market/properties/{prop_id}/roi",
            json={"intention": "aluguel", "horizon_months": 60, "area_sqm": 70.0},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["yield_annual_pct"] is not None
    assert body["payback_months"] is not None


def test_post_roi_property_not_found(client, seeded):
    r = client.post(
        f"/market/properties/{uuid.uuid4()}/roi",
        json={"intention": "revenda"},
    )
    assert r.status_code == 404
