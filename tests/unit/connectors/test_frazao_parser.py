from decimal import Decimal
from pathlib import Path

from app.connectors.frazao.collector import FrazaoConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"


def _props():
    raw = (FIXTURES / "frazao_list.html").read_bytes()
    return list(FrazaoConnector().parse(raw, "https://www.frazaoleiloes.com.br/lotes/busca/p/1"))


def test_frazao_extracts_two():
    props = _props()
    assert len(props) == 2
    assert all(p.bank_code == "frazao" for p in props)


def test_frazao_external_codes():
    codes = {p.external_code for p in _props()}
    assert codes == {"401", "402"}


def test_frazao_normalize_first():
    norm = FrazaoConnector().normalize(_props()[0])
    assert norm["bank_code"] == "frazao"
    assert norm["city"] == "Recife"
    assert norm["state"] == "PE"
    assert norm["current_value"] == Decimal("195000.00")


def test_frazao_empty_bytes_yields_nothing():
    assert list(FrazaoConnector().parse(b"", "https://example.com")) == []
