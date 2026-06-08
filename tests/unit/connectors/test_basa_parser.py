from datetime import date
from decimal import Decimal
from pathlib import Path

from app.connectors.basa import BASAConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"


def test_basa_pdf_extracts_three():
    raw = (FIXTURES / "basa_edital.pdf").read_bytes()
    props = list(BASAConnector().parse(raw, "https://www.bancoamazonia.com.br/edital03.pdf"))
    assert len(props) == 3
    assert all(p.bank_code == "basa" for p in props)


def test_basa_normalize_edital_meta():
    raw = (FIXTURES / "basa_edital.pdf").read_bytes()
    p = list(BASAConnector().parse(raw, "https://www.bancoamazonia.com.br/edital03.pdf"))[0]
    norm = BASAConnector().normalize(p)
    assert norm["bank_code"] == "basa"
    assert norm["city"] == "Belém"
    assert norm["state"] == "PA"
    assert norm["sale_modality"] == "Leilão"
    assert norm["edital_number"] == "03/2026"
    assert norm["auction_date"] == date(2026, 7, 15)
    assert norm["current_value"] == Decimal("196000.00")
    assert norm["edital_url"].endswith("edital03.pdf")


def test_basa_index_html_yields_nothing():
    html = b"<html><body><a href='/edital03.pdf'>Edital</a></body></html>"
    props = list(BASAConnector().parse(html, "https://www.bancoamazonia.com.br/imoveis-e-bens"))
    assert props == []
