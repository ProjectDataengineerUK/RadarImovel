from decimal import Decimal
from pathlib import Path

from app.connectors.zuk.collector import ZukConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"


def _props():
    raw = (FIXTURES / "zuk_list.html").read_bytes()
    return list(ZukConnector().parse(raw, "https://www.portalzuk.com.br/imoveis"))


def test_zuk_extracts_two():
    props = _props()
    assert len(props) == 2
    assert all(p.bank_code == "zuk" for p in props)


def test_zuk_external_codes():
    props = _props()
    codes = {p.external_code for p in props}
    assert codes == {"ZUK-001", "ZUK-002"}


def test_zuk_normalize_first():
    norm = ZukConnector().normalize(_props()[0])
    assert norm["bank_code"] == "zuk"
    assert norm["city"] == "São Paulo"
    assert norm["state"] == "SP"
    assert norm["current_value"] == Decimal("350000.00")
    assert norm["property_type"] == "Apartamento"


def test_zuk_normalize_second():
    norm = ZukConnector().normalize(_props()[1])
    assert norm["city"] == "Campinas"
    assert norm["current_value"] == Decimal("480000.00")


def test_zuk_empty_bytes_yields_nothing():
    props = list(ZukConnector().parse(b"", "https://example.com"))
    assert props == []


def test_zuk_no_cards_yields_nothing():
    props = list(ZukConnector().parse(b"<html><body><p>nada</p></body></html>", "https://example.com"))
    assert props == []
