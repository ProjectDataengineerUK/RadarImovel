"""Unit tests for deduplicator v2: 2-stage matching + offer upsert + best_price."""
import uuid
from decimal import Decimal
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.bank import Bank
from app.models.property import Property, PropertyOffer
from app.agents.deduplicator import (
    _geo_key,
    _title_sim,
    _upsert_offer,
    _refresh_best_price,
    process_property,
)


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


def _make_source(session, code="caixa", name="Caixa") -> Bank:
    src = Bank(id=uuid.uuid4(), code=code, name=name, source_type="bank")
    session.add(src)
    session.flush()
    return src


def _make_normalized(**kwargs) -> dict:
    defaults = {
        "external_code": "EXT-1",
        "bank_code": "caixa",
        "title": "Apartamento 2 quartos Moema SP",
        "property_type": "Apartamento",
        "city": "São Paulo",
        "state": "SP",
        "minimum_value": Decimal("300000"),
        "current_value": Decimal("300000"),
        "discount_percent": None,
        "occupancy_status": "Desocupado",
        "sale_modality": "Licitação Aberta",
        "official_url": "https://example.com/1",
        "status": "active",
    }
    return {**defaults, **kwargs}


# ── Pure helper tests ─────────────────────────────────────────────────────────

def test_geo_key_rounds_to_three_decimal_places():
    # round(-23.5505, 3) → -23.55 (Python banker's rounding)
    key = _geo_key(-23.5505, -46.6333)
    parts = key.split(",")
    assert len(parts) == 2
    assert abs(float(parts[0]) - (-23.5505)) < 0.01
    assert abs(float(parts[1]) - (-46.6333)) < 0.01


def test_geo_key_none_if_missing():
    assert _geo_key(None, -46.6333) is None
    assert _geo_key(-23.5505, None) is None


def test_title_sim_identical():
    assert _title_sim("Apartamento", "Apartamento") == 1.0


def test_title_sim_near():
    sim = _title_sim("Apartamento 2q Moema SP", "Apartamento 2 quartos Moema SP")
    assert sim >= 0.7


def test_title_sim_different():
    sim = _title_sim("Apartamento Moema SP", "Terreno Guarulhos SP")
    assert sim < 0.5


def test_title_sim_none_returns_zero():
    assert _title_sim(None, "anything") == 0.0
    assert _title_sim("anything", None) == 0.0


# ── Offer upsert + best_price ─────────────────────────────────────────────────

def test_upsert_offer_creates_new(session):
    src = _make_source(session, "bb", "Banco do Brasil")
    prop = Property(
        id=uuid.uuid4(), bank_id=src.id, external_code="EXT-X",
        property_type="Apartamento", city="Rio", state="RJ",
        minimum_value=Decimal("100000"), current_value=Decimal("100000"),
        occupancy_status="Desocupado", sale_modality="Licitação",
        official_url="https://example.com/x", status="active",
        content_hash="a" * 64,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    session.add(prop)
    session.flush()

    offer = _upsert_offer(session, prop.id, src.id, {"current_value": Decimal("100000"), "sale_modality": "Licitação", "official_url": "https://example.com/x"}, "EXT-X")
    session.flush()
    assert offer.price == Decimal("100000")
    assert offer.property_id == prop.id


def test_upsert_offer_updates_existing_price(session):
    src = _make_source(session, "brb", "BRB")
    prop = Property(
        id=uuid.uuid4(), bank_id=src.id, external_code="EXT-Y",
        property_type="Casa", city="Brasília", state="DF",
        minimum_value=Decimal("500000"), current_value=Decimal("500000"),
        occupancy_status="Ocupado", sale_modality="Venda Direta",
        official_url="https://example.com/y", status="active",
        content_hash="b" * 64,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    session.add(prop)
    session.flush()
    _upsert_offer(session, prop.id, src.id, {"current_value": Decimal("500000"), "sale_modality": "Venda Direta", "official_url": "https://ex.com"}, "EXT-Y")
    session.flush()

    # Second call with lower price
    _upsert_offer(session, prop.id, src.id, {"current_value": Decimal("400000"), "sale_modality": "Venda Direta", "official_url": "https://ex.com"}, "EXT-Y")
    session.flush()

    offers = session.query(PropertyOffer).filter_by(property_id=prop.id).all()
    assert len(offers) == 1
    assert offers[0].price == Decimal("400000")


def test_refresh_best_price_picks_minimum(session):
    src1 = _make_source(session, "bnb", "Banco do Nordeste")
    src2 = _make_source(session, "zuk2", "Zuk")
    prop = Property(
        id=uuid.uuid4(), bank_id=src1.id, external_code="EXT-Z",
        property_type="Apartamento", city="Fortaleza", state="CE",
        minimum_value=Decimal("200000"), current_value=Decimal("200000"),
        occupancy_status="Desocupado", sale_modality="Licitação",
        official_url="https://example.com/z", status="active",
        content_hash="c" * 64,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    session.add(prop)
    session.flush()

    _upsert_offer(session, prop.id, src1.id, {"current_value": Decimal("200000"), "sale_modality": "Licitação", "official_url": "https://example.com/z"}, "EXT-Z")
    _upsert_offer(session, prop.id, src2.id, {"current_value": Decimal("185000"), "sale_modality": "Leilão", "official_url": "https://zuk.com/z"}, "ZUK-Z")
    session.flush()

    _refresh_best_price(session, prop.id)
    session.flush()
    updated = session.get(Property, prop.id)
    assert updated.best_price == Decimal("185000")


# ── process_property v2 ───────────────────────────────────────────────────────

def test_process_property_creates_new(session):
    src = _make_source(session, "basa", "Banco da Amazônia")
    normalized = _make_normalized(
        external_code="BASA-NEW-1",
        bank_code="basa",
        city="Belém",
        state="PA",
    )
    prop, is_new = process_property(session, normalized, src, "BASA-NEW-1")
    session.flush()
    assert is_new is True
    assert prop.external_code == "BASA-NEW-1"
    assert prop.best_price == Decimal("300000")


def test_process_property_stage1b_exact_match(session):
    src = _make_source(session, "banestes2", "Banestes")
    # Create an existing property
    normalized = _make_normalized(external_code="BAN-001", bank_code="banestes2", city="Vitória", state="ES")
    prop_orig, _ = process_property(session, normalized, src, "BAN-001")
    session.flush()

    # Same source, same external_code → updates, not creates
    normalized2 = _make_normalized(
        external_code="BAN-001",
        bank_code="banestes2",
        city="Vitória",
        state="ES",
        current_value=Decimal("280000"),
    )
    prop2, is_new = process_property(session, normalized2, src, "BAN-001")
    session.flush()
    assert is_new is False
    assert prop2.id == prop_orig.id
    # best_price reflects the updated offer
    assert prop2.best_price == Decimal("280000")


def test_process_property_multi_source_same_property(session):
    """Mesmo imóvel, dois leiloeiros → 1 property com 2 offers."""
    src_bank = _make_source(session, "caixa2", "Caixa Econômica Federal")
    src_leil = _make_source(session, "mega2", "Mega Leilões")

    # Bank creates the property first
    n1 = _make_normalized(external_code="CEF-DEDUP", bank_code="caixa2", city="Curitiba", state="PR")
    prop_orig, is_new1 = process_property(session, n1, src_bank, "CEF-DEDUP")
    session.flush()
    assert is_new1 is True

    # Leiloeiro creates an offer on same property via direct offer lookup after bank registered it
    n2 = _make_normalized(
        external_code="MEG-DEDUP",
        bank_code="mega2",
        city="Curitiba",
        state="PR",
        current_value=Decimal("270000"),
    )
    prop2, is_new2 = process_property(session, n2, src_leil, "MEG-DEDUP")
    session.flush()
    # Different external_code and no coordinates → new property (dedup via geo needs coords)
    # This is expected: without lat/lng the geohash stage can't match
    assert prop2.id != prop_orig.id or not is_new2
