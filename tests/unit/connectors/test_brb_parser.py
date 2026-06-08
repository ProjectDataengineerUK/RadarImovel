from decimal import Decimal
from pathlib import Path

from app.connectors.brb import BRBConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"


def test_brb_html_extracts_three():
    raw = (FIXTURES / "brb_list.html").read_bytes()
    props = list(BRBConnector().parse(raw, "https://www.brb.com.br/imoveis"))
    assert len(props) == 3
    assert all(p.bank_code == "brb" for p in props)
    assert all(p.source_name == "brb_oficial" for p in props)


def test_brb_html_normalize():
    raw = (FIXTURES / "brb_list.html").read_bytes()
    p = list(BRBConnector().parse(raw, "https://www.brb.com.br/imoveis"))[0]
    norm = BRBConnector().normalize(p)
    assert norm["bank_code"] == "brb"
    assert norm["state"] == "DF"
    assert isinstance(norm["current_value"], Decimal)
    assert norm["sale_modality"] == "Venda direta"


def test_brb_resale_json_extracts_three():
    raw = (FIXTURES / "brb_resale.json").read_bytes()
    props = list(BRBConnector().parse(raw, "https://brb.resale.com.br/api/imoveis"))
    assert len(props) == 3
    assert {p.external_code for p in props} == {"RES-3001", "RES-3002", "RES-3003"}
    assert all(p.source_name == "brb_resale" for p in props)


def test_brb_resale_normalize_modality():
    raw = (FIXTURES / "brb_resale.json").read_bytes()
    p = list(BRBConnector().parse(raw, "https://brb.resale.com.br/api/imoveis"))[0]
    norm = BRBConnector().normalize(p)
    assert norm["sale_modality"] == "Venda direta (Resale)"
    assert norm["current_value"] == Decimal("210000.00")
    assert norm["official_url"].startswith("https://brb.resale.com.br")
