"""Tests para BBParser usando fixture real de seuimovelbb.com.br/."""
from decimal import Decimal
from pathlib import Path

from app.connectors.bb import BBConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"
SOURCE_URL = "https://seuimovelbb.com.br/"


def _props():
    raw = (FIXTURES / "bb_list.html").read_bytes()
    return list(BBConnector().parse(raw, SOURCE_URL))


def test_bb_extracts_cards():
    props = _props()
    assert len(props) >= 1
    assert all(p.bank_code == "bb" for p in props)
    assert all(p.source_name == "bb_seuimovelbb" for p in props)


def test_bb_external_codes_are_numeric():
    # BB IDs come from _compartilhar('ID74833 ...') → "74833"
    props = _props()
    codes = [p.external_code for p in props]
    assert all(c.isdigit() or c != "" for c in codes), f"Non-numeric codes: {[c for c in codes if not c.isdigit()]}"


def test_bb_has_city_state():
    props = _props()
    norms = [BBConnector().normalize(p) for p in props]
    for n in norms:
        assert len(n["state"]) == 2, f"Bad state: {n['state']}"
        assert n["city"] != "", f"Missing city for {n['external_code']}"


def test_bb_has_current_value():
    props = _props()
    norms = [BBConnector().normalize(p) for p in props]
    for n in norms:
        assert isinstance(n["current_value"], Decimal)
        assert n["current_value"] > Decimal("0")


def test_bb_has_sale_modality():
    props = _props()
    modalities = {BBConnector().normalize(p)["sale_modality"] for p in props}
    assert modalities & {"Leilão", "Venda direta"}, f"Unexpected modalities: {modalities}"


def test_bb_official_url():
    props = _props()
    for p in props:
        url = p.raw_data.get("official_url", "")
        assert url.startswith("https://seuimovelbb.com.br/imovel/id/"), f"Bad URL: {url}"


def test_bb_empty_bytes():
    assert list(BBConnector().parse(b"", SOURCE_URL)) == []


def test_bb_normalize_schema_keys():
    p = _props()[0]
    norm = BBConnector().normalize(p)
    required = {"external_code", "bank_code", "city", "state", "current_value", "sale_modality", "official_url"}
    assert required <= norm.keys()
