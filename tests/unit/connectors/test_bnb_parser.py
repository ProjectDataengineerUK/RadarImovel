from decimal import Decimal
from pathlib import Path

from app.connectors.bnb import BNBConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"


def test_bnb_html_extracts_three():
    raw = (FIXTURES / "bnb_list.html").read_bytes()
    props = list(BNBConnector().parse(raw, "https://www.bnb.gov.br/bens-em-oferta"))
    assert len(props) == 3
    assert all(p.bank_code == "bnb" for p in props)


def test_bnb_html_normalize():
    raw = (FIXTURES / "bnb_list.html").read_bytes()
    p = list(BNBConnector().parse(raw, "https://www.bnb.gov.br/bens-em-oferta"))[0]
    norm = BNBConnector().normalize(p)
    assert norm["bank_code"] == "bnb"
    assert norm["city"] == "Fortaleza"
    assert norm["state"] == "CE"
    assert norm["current_value"] == Decimal("200000.00")
    assert norm["appraisal_value"] == Decimal("250000.00")
    assert norm["discount_percent"] == Decimal("20.00")


def test_bnb_pdf_extracts_three():
    raw = (FIXTURES / "bnb_relacao.pdf").read_bytes()
    props = list(BNBConnector().parse(raw, "https://www.bnb.gov.br/relacao.pdf"))
    assert len(props) == 3
    norm = BNBConnector().normalize(props[0])
    assert norm["bank_code"] == "bnb"
    assert norm["city"] == "Mossoró"
    assert norm["state"] == "RN"
    assert isinstance(norm["current_value"], Decimal)
    assert norm["edital_url"] == "https://www.bnb.gov.br/relacao.pdf"
