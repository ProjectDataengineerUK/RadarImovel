"""Tests para BanestesParser usando PDF real de edital (leilao-imovel-010-2026)."""
from decimal import Decimal
from pathlib import Path

from app.connectors.banestes import BanestesConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"
PDF_URL = "https://www.banestes.com.br/publicacoes_legais/arquivos_colic/2026/leilao-imovel-010-2026.pdf"


def _props():
    raw = (FIXTURES / "banestes_edital.pdf").read_bytes()
    return list(BanestesConnector().parse(raw, PDF_URL))


def test_banestes_pdf_extracts_rows():
    props = _props()
    assert len(props) >= 4
    assert all(p.bank_code == "banestes" for p in props)
    assert all(p.source_name == "banestes_edital_pdf" for p in props)


def test_banestes_pdf_numeric_external_codes():
    props = _props()
    codes = [p.external_code for p in props]
    assert "1" in codes
    assert "2" in codes
    assert "3" in codes
    assert "4" in codes


def test_banestes_state_es():
    props = _props()
    norms = [BanestesConnector().normalize(p) for p in props]
    for n in norms:
        assert n["state"] == "ES", f"Unexpected state: {n['state']} for {n['external_code']}"


def test_banestes_first_property():
    props = _props()
    lote1 = next(p for p in props if p.external_code == "1")
    norm = BanestesConnector().normalize(lote1)
    assert norm["bank_code"] == "banestes"
    assert norm["city"] == "Anchieta"
    assert norm["state"] == "ES"
    assert norm["current_value"] == Decimal("8900000.00")
    assert norm["sale_modality"] == "Leilão"
    assert norm["occupancy_status"] == "Desocupado"


def test_banestes_edital_number():
    props = _props()
    for p in props[:4]:
        norm = BanestesConnector().normalize(p)
        assert norm["edital_number"] == "010/2026"


def test_banestes_official_url():
    props = _props()
    for p in props[:4]:
        assert p.raw_data["official_url"] == PDF_URL


def test_banestes_index_html_yields_nothing():
    html = b"<html><body><a href='/edital07.pdf'>Edital</a></body></html>"
    props = list(BanestesConnector().parse(html, "https://www.banestes.com.br/leiloes-e-vendas"))
    assert props == []


def test_banestes_empty_bytes():
    assert list(BanestesConnector().parse(b"", PDF_URL)) == []
