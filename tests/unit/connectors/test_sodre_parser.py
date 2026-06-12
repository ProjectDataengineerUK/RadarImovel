from decimal import Decimal
from pathlib import Path

from app.connectors.sodre.collector import SodreConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"


def _props():
    raw = (FIXTURES / "sodre_list.html").read_bytes()
    return list(SodreConnector().parse(raw, "https://www.sodresantoro.com.br/lotes"))


def test_sodre_extracts_two():
    props = _props()
    assert len(props) == 2
    assert all(p.bank_code == "sodre" for p in props)


def test_sodre_external_codes():
    codes = {p.external_code for p in _props()}
    assert codes == {"SODRE-201", "SODRE-202"}


def test_sodre_normalize_first():
    norm = SodreConnector().normalize(_props()[0])
    assert norm["bank_code"] == "sodre"
    assert norm["city"] == "Barueri"
    assert norm["state"] == "SP"
    assert norm["current_value"] == Decimal("250000.00")


def test_sodre_empty_bytes_yields_nothing():
    assert list(SodreConnector().parse(b"", "https://example.com")) == []
