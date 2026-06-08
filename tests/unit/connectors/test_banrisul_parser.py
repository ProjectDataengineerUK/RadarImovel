from decimal import Decimal
from pathlib import Path

from app.connectors.banrisul import BanrisulConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"


def _props():
    raw = (FIXTURES / "banrisul_list.html").read_bytes()
    return list(BanrisulConnector().parse(raw, "https://www.banrisul.com.br/bens"))


def test_banrisul_extracts_three():
    props = _props()
    assert len(props) == 3
    assert all(p.bank_code == "banrisul" for p in props)


def test_banrisul_normalize():
    norm = BanrisulConnector().normalize(_props()[0])
    assert norm["bank_code"] == "banrisul"
    assert norm["city"] == "Porto Alegre"
    assert norm["state"] == "RS"
    assert norm["current_value"] == Decimal("280000.00")
    assert norm["discount_percent"] == Decimal("20.00")


def test_banrisul_default_state_rs():
    # Segundo card não tem UF no fixture; deve assumir RS.
    norm = BanrisulConnector().normalize(_props()[1])
    assert norm["state"] == "RS"
