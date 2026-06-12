"""
Testes de integração: multi-fonte (AT-007 / AT-011) — PropertyOffer + best_price.
Valida que o mesmo imóvel indexado por banco e leiloeiro gera 2 offers, 1 property.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone

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
from app.models.property import Property, PropertyOffer
from app.models.user import User
from app.agents.deduplicator import process_property, _upsert_offer, _refresh_best_price


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
    s = Session()
    yield s
    s.rollback()
    s.close()


@pytest.fixture
def client(db):
    def override_db():
        yield db

    uid = f"uid-offers-{uuid.uuid4().hex[:8]}"
    user = User(id=uuid.uuid4(), firebase_uid=uid, email=f"{uid}@test.com", role="user")
    db.add(user)
    db.flush()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    yield TestClient(app)
    app.dependency_overrides.clear()


def _src(db, code, name, stype="bank") -> Bank:
    existing = db.query(Bank).filter_by(code=code).first()
    if existing:
        return existing
    src = Bank(id=uuid.uuid4(), code=code, name=name, source_type=stype)
    db.add(src)
    db.flush()
    return src


def _norm(code, bank_code, city="São Paulo", state="SP", value=Decimal("300000")) -> dict:
    return {
        "external_code": code,
        "bank_code": bank_code,
        "title": f"Apartamento {code}",
        "property_type": "Apartamento",
        "city": city,
        "state": state,
        "minimum_value": value,
        "current_value": value,
        "occupancy_status": "Desocupado",
        "sale_modality": "Licitação Aberta",
        "official_url": f"https://example.com/{code}",
        "status": "active",
    }


# ── AT-007 / AT-011 ───────────────────────────────────────────────────────────

def test_two_sources_same_external_code_same_source_creates_one_offer(db):
    """Mesma fonte + mesmo external_code → upsert de offer (não duplica)."""
    src = _src(db, "caixa_it", "Caixa")
    n = _norm("IT-001", "caixa_it")

    _, is_new1 = process_property(db, n, src, "IT-001")
    db.flush()
    _, is_new2 = process_property(db, {**n, "current_value": Decimal("280000")}, src, "IT-001")
    db.flush()

    assert is_new1 is True
    assert is_new2 is False
    offers = db.query(PropertyOffer).filter_by(source_id=src.id).all()
    active = [o for o in offers if o.external_code == "IT-001" and o.active]
    assert len(active) == 1
    assert active[0].price == Decimal("280000")


def test_best_price_is_minimum_across_offers(db):
    """best_price = menor preço entre as offers ativas."""
    src_bank = _src(db, "bb_it", "Banco do Brasil")
    src_leil = _src(db, "zuk_it", "Zuk", stype="auctioneer")

    prop = Property(
        id=uuid.uuid4(), bank_id=src_bank.id, external_code="BP-001",
        property_type="Casa", city="Salvador", state="BA",
        minimum_value=Decimal("400000"), current_value=Decimal("400000"),
        occupancy_status="Desocupado", sale_modality="Licitação",
        official_url="https://example.com/bp1", status="active",
        content_hash="z" * 64,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db.add(prop)
    db.flush()

    _upsert_offer(db, prop.id, src_bank.id, {"current_value": Decimal("400000"), "sale_modality": "Licitação", "official_url": "https://example.com/bp1"}, "BP-001")
    _upsert_offer(db, prop.id, src_leil.id, {"current_value": Decimal("370000"), "sale_modality": "Leilão", "official_url": "https://zuk.com/bp1"}, "ZUK-BP1")
    db.flush()
    _refresh_best_price(db, prop.id)
    db.flush()

    refreshed = db.get(Property, prop.id)
    assert refreshed.best_price == Decimal("370000")


def test_offers_endpoint_returns_active_offers(client, db):
    """GET /properties/{id}/offers retorna offers ativas ordenadas por preço."""
    src = _src(db, "bnb_it", "BNB")
    src2 = _src(db, "sodre_it", "Sodré Santoro", stype="auctioneer")

    prop = Property(
        id=uuid.uuid4(), bank_id=src.id, external_code="OFF-001",
        property_type="Apartamento", city="Fortaleza", state="CE",
        minimum_value=Decimal("200000"), current_value=Decimal("200000"),
        occupancy_status="Desocupado", sale_modality="Licitação",
        official_url="https://example.com/off1", status="active",
        content_hash="y" * 64,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db.add(prop)
    db.flush()

    _upsert_offer(db, prop.id, src.id, {"current_value": Decimal("200000"), "sale_modality": "Licitação", "official_url": "https://example.com/off1"}, "OFF-001")
    _upsert_offer(db, prop.id, src2.id, {"current_value": Decimal("185000"), "sale_modality": "Leilão", "official_url": "https://sodre.com/off1"}, "SODRE-OFF1")
    db.commit()

    resp = client.get(f"/properties/{prop.id}/offers")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    prices = [o["price"] for o in data]
    assert prices == sorted(prices)  # ordered by price ascending


def test_offers_endpoint_404_for_unknown_property(client):
    resp = client.get(f"/properties/{uuid.uuid4()}/offers")
    assert resp.status_code == 404


def test_dedup_flag_cleared_via_api(client, db):
    """DELETE /admin/dedup/{id}/flag limpa o possible_duplicate_of."""
    src = _src(db, "brb_it", "BRB")
    uid = f"uid-admin-dedup-{uuid.uuid4().hex[:8]}"
    admin = User(
        id=uuid.uuid4(), firebase_uid=uid,
        email=f"{uid}@test.com", role="operador"
    )
    db.add(admin)
    db.flush()

    prop = Property(
        id=uuid.uuid4(), bank_id=src.id, external_code="DUP-001",
        property_type="Casa", city="Brasília", state="DF",
        minimum_value=Decimal("500000"), current_value=Decimal("500000"),
        occupancy_status="Ocupado", sale_modality="Venda",
        official_url="https://example.com/dup1", status="active",
        content_hash="w" * 64,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        possible_duplicate_of=uuid.uuid4(),
    )
    db.add(prop)
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: admin
    resp = client.delete(f"/admin/dedup/{prop.id}/flag")
    assert resp.status_code == 200
    db.refresh(prop)
    assert prop.possible_duplicate_of is None
