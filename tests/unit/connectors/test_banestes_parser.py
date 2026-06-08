from datetime import date
from decimal import Decimal
from pathlib import Path

from app.connectors.banestes import BanestesConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"


def test_banestes_pdf_extracts_three():
    raw = (FIXTURES / "banestes_edital.pdf").read_bytes()
    props = list(BanestesConnector().parse(raw, "https://www.banestes.com.br/edital07.pdf"))
    assert len(props) == 3
    assert all(p.bank_code == "banestes" for p in props)


def test_banestes_normalize_edital_meta():
    raw = (FIXTURES / "banestes_edital.pdf").read_bytes()
    p = list(BanestesConnector().parse(raw, "https://www.banestes.com.br/edital07.pdf"))[0]
    norm = BanestesConnector().normalize(p)
    assert norm["bank_code"] == "banestes"
    assert norm["city"] == "Vitória"
    assert norm["state"] == "ES"
    assert norm["sale_modality"] == "Leilão"
    assert norm["edital_number"] == "07/2026"
    assert norm["auction_date"] == date(2026, 8, 22)
    assert norm["current_value"] == Decimal("280000.00")


def test_banestes_index_html_yields_nothing():
    html = b"<html><body><a href='/edital07.pdf'>Edital</a></body></html>"
    props = list(BanestesConnector().parse(html, "https://www.banestes.com.br/leiloes-e-vendas"))
    assert props == []
