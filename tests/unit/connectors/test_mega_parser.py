from decimal import Decimal
from pathlib import Path

from app.connectors.mega.collector import MegaConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"


def _props():
    raw = (FIXTURES / "mega_list.html").read_bytes()
    return list(MegaConnector().parse(raw, "https://www.megaleiloes.com.br/imoveis"))


def test_mega_extracts_two():
    props = _props()
    assert len(props) == 2
    assert all(p.bank_code == "mega" for p in props)


def test_mega_external_codes():
    codes = {p.external_code for p in _props()}
    assert codes == {"J12345", "J67890"}


def test_mega_normalize_first():
    norm = MegaConnector().normalize(_props()[0])
    assert norm["bank_code"] == "mega"
    assert norm["city"] == "Rio de Janeiro"
    assert norm["state"] == "RJ"
    assert norm["current_value"] == Decimal("620000.00")


def test_mega_empty_bytes_yields_nothing():
    assert list(MegaConnector().parse(b"", "https://example.com")) == []
