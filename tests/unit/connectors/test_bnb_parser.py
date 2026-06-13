from decimal import Decimal
from pathlib import Path

from app.connectors.bnb import BNBConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"


def _props():
    raw = (FIXTURES / "bnb_relacao.pdf").read_bytes()
    return list(BNBConnector().parse(raw, "https://www.bnb.gov.br/relacao.pdf"))


def test_bnb_pdf_extracts_rows():
    props = _props()
    assert len(props) >= 1
    assert all(p.bank_code == "bnb" for p in props)


def test_bnb_pdf_external_codes():
    props = _props()
    codes = [p.external_code for p in props]
    assert "01" in codes or "1" in codes or any(c.isdigit() for c in codes)


def test_bnb_pdf_normalize_city_state():
    norm = BNBConnector().normalize(_props()[1])  # lote 02 — Missão Velha, CE
    assert norm["bank_code"] == "bnb"
    assert norm["state"] == "CE"
    assert norm["city"] == "Missão Velha"
    assert norm["current_value"] == Decimal("492000.00")
    assert norm["edital_url"] == "https://www.bnb.gov.br/relacao.pdf"


def test_bnb_pdf_sergipe_rows():
    props = _props()
    norms = [BNBConnector().normalize(p) for p in props]
    se_rows = [n for n in norms if n["state"] == "SE"]
    assert len(se_rows) >= 1
    assert all(n["city"] == "Propriá" for n in se_rows)
    assert all(isinstance(n["current_value"], Decimal) for n in se_rows)
