from decimal import Decimal
from pathlib import Path

from app.connectors.bb import BBConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"


def _props():
    raw = (FIXTURES / "bb_list.html").read_bytes()
    return list(BBConnector().parse(raw, "https://www21.bb.com.br/portalbb/lista"))


def test_bb_parser_extracts_three():
    assert len(_props()) == 3


def test_bb_parser_bank_code_and_codes():
    props = _props()
    assert all(p.bank_code == "bb" for p in props)
    assert {p.external_code for p in props} == {"BB-1001", "BB-1002", "BB-1003"}


def test_bb_normalize_schema():
    p = _props()[0]
    norm = BBConnector().normalize(p)
    assert norm["bank_code"] == "bb"
    assert norm["external_code"] == "BB-1001"
    assert norm["state"] == "GO" and len(norm["state"]) == 2
    assert norm["city"] == "Goiânia"
    assert isinstance(norm["current_value"], Decimal)
    assert norm["current_value"] == Decimal("180000.00")
    assert norm["property_type"] == "Apartamento"


def test_bb_normalize_computes_discount():
    norm = BBConnector().normalize(_props()[0])
    assert norm["discount_percent"] == Decimal("25.00")


def test_bb_empty_bytes():
    assert list(BBConnector().parse(b"", "https://x")) == []
