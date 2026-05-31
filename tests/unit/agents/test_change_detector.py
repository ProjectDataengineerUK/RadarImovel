from unittest.mock import MagicMock, call
from decimal import Decimal
from app.agents.change_detector import detect_and_record_changes, MONITORED_FIELDS


def make_property(**kwargs):
    defaults = {
        "id": "prop-uuid",
        "current_value": Decimal("200000"),
        "minimum_value": Decimal("180000"),
        "discount_percent": Decimal("25"),
        "occupancy_status": "Desocupado",
        "sale_modality": "Licitação Aberta",
        "status": "active",
        "auction_date": None,
    }
    prop = MagicMock()
    for k, v in {**defaults, **kwargs}.items():
        setattr(prop, k, v)
    return prop


def test_detects_price_change():
    prop = make_property(current_value=Decimal("200000"))
    session = MagicMock()
    changes = detect_and_record_changes(session, prop, {"current_value": 180000, "minimum_value": 180000,
        "discount_percent": 25, "occupancy_status": "Desocupado", "sale_modality": "Licitação Aberta",
        "status": "active", "auction_date": None})
    assert any(c.field_name == "current_value" for c in changes)


def test_no_change_returns_empty():
    prop = make_property()
    session = MagicMock()
    normalized = {
        "current_value": Decimal("200000"),
        "minimum_value": Decimal("180000"),
        "discount_percent": Decimal("25"),
        "occupancy_status": "Desocupado",
        "sale_modality": "Licitação Aberta",
        "status": "active",
        "auction_date": None,
    }
    changes = detect_and_record_changes(session, prop, normalized)
    assert changes == []


def test_records_old_and_new_values():
    prop = make_property(current_value=Decimal("200000"))
    session = MagicMock()
    changes = detect_and_record_changes(session, prop, {"current_value": 150000, "minimum_value": Decimal("180000"),
        "discount_percent": Decimal("25"), "occupancy_status": "Desocupado",
        "sale_modality": "Licitação Aberta", "status": "active", "auction_date": None})
    price_change = next(c for c in changes if c.field_name == "current_value")
    assert price_change.old_value == "200000"
    assert price_change.new_value == "150000"


def test_adds_changes_to_session():
    prop = make_property(occupancy_status="Ocupado")
    session = MagicMock()
    detect_and_record_changes(session, prop, {"current_value": Decimal("200000"), "minimum_value": Decimal("180000"),
        "discount_percent": Decimal("25"), "occupancy_status": "Desocupado",
        "sale_modality": "Licitação Aberta", "status": "active", "auction_date": None})
    assert session.add.called


def test_all_monitored_fields_covered():
    assert set(MONITORED_FIELDS) == {
        "current_value", "minimum_value", "discount_percent",
        "occupancy_status", "sale_modality", "status", "auction_date"
    }
