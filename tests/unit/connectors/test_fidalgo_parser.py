from decimal import Decimal
from pathlib import Path

from app.connectors.fidalgo.collector import FidalgoConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"


def _props():
    raw = (FIXTURES / "fidalgo_list.html").read_bytes()
    return list(FidalgoConnector().parse(raw, "https://www.fidalgoleiloes.com.br/imoveis"))


def test_fidalgo_extracts_two():
    props = _props()
    assert len(props) == 2
    assert all(p.bank_code == "fidalgo" for p in props)


def test_fidalgo_external_codes():
    codes = {p.external_code for p in _props()}
    assert codes == {"FID-301", "FID-302"}


def test_fidalgo_normalize_first():
    norm = FidalgoConnector().normalize(_props()[0])
    assert norm["bank_code"] == "fidalgo"
    assert norm["city"] == "São Paulo"
    assert norm["state"] == "SP"
    assert norm["current_value"] == Decimal("790000.00")


def test_fidalgo_empty_bytes_yields_nothing():
    assert list(FidalgoConnector().parse(b"", "https://example.com")) == []
