"""Tests para BRBParser usando fixture brb_list.html com classes CSS module reais."""
from decimal import Decimal
from pathlib import Path

from app.connectors.brb import BRBConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"
SOURCE_URL = "https://feiraobrb.com.br/busca"


def _props():
    raw = (FIXTURES / "brb_list.html").read_bytes()
    return list(BRBConnector().parse(raw, SOURCE_URL))


def test_brb_extracts_three_cards():
    props = _props()
    assert len(props) == 3
    assert all(p.bank_code == "brb" for p in props)
    assert all(p.source_name == "brb_resale" for p in props)


def test_brb_external_codes():
    props = _props()
    codes = [p.external_code for p in props]
    assert codes == ["1001", "1002", "1003"]


def test_brb_official_urls():
    props = _props()
    for p in props:
        url = p.raw_data["official_url"]
        assert url.startswith("https://feiraobrb.com.br/imovel/"), f"Bad URL: {url}"


def test_brb_state():
    props = _props()
    norms = [BRBConnector().normalize(p) for p in props]
    for n in norms:
        assert n["state"] == "DF"


def test_brb_current_value():
    props = _props()
    norms = [BRBConnector().normalize(p) for p in props]
    values = [n["current_value"] for n in norms]
    assert values[0] == Decimal("650000.00")
    assert values[1] == Decimal("480000.00")
    assert values[2] == Decimal("210000.00")


def test_brb_sale_modality():
    props = _props()
    norms = [BRBConnector().normalize(p) for p in props]
    modalities = [n["sale_modality"] for n in norms]
    assert modalities[0] == "Venda direta"
    assert modalities[1] == "Leilão"
    assert modalities[2] == "Venda direta"


def test_brb_title():
    props = _props()
    titles = [p.raw_data["title"] for p in props]
    assert "Apartamento" in titles[0]
    assert "Casa" in titles[1]
    assert "Sala Comercial" in titles[2]


def test_brb_empty_bytes():
    assert list(BRBConnector().parse(b"", SOURCE_URL)) == []


def test_brb_normalize_schema_keys():
    p = _props()[0]
    norm = BRBConnector().normalize(p)
    required = {"external_code", "bank_code", "state", "current_value", "sale_modality", "official_url"}
    assert required <= norm.keys()
