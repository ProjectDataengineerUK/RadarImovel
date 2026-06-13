from decimal import Decimal
from pathlib import Path

from app.connectors.fidalgo.collector import FidalgoConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"


def _props():
    raw = (FIXTURES / "fidalgo_list.html").read_bytes()
    return list(FidalgoConnector().parse(raw, "https://www.fidalgoleiloes.com.br/leilao.php?idLeilao=9999"))


def test_fidalgo_extracts_two():
    props = _props()
    # fixture has 2 active lots + 1 withdrawn (loteRetirado) that must be skipped
    assert len(props) == 2
    assert all(p.bank_code == "fidalgo" for p in props)


def test_fidalgo_external_codes():
    codes = {p.external_code for p in _props()}
    assert codes == {"301", "302"}


def test_fidalgo_normalize_first():
    norm = FidalgoConnector().normalize(_props()[0])
    assert norm["bank_code"] == "fidalgo"
    assert norm["current_value"] == Decimal("790000.00")
    # City/state not available in Fidalgo HTML (only in full address text)
    assert norm["state"] == "SP"  # default fallback


def test_fidalgo_skips_withdrawn():
    # loteRetirado lot must not appear
    codes = {p.external_code for p in _props()}
    assert "303" not in codes


def test_fidalgo_empty_bytes_yields_nothing():
    assert list(FidalgoConnector().parse(b"", "https://example.com")) == []
