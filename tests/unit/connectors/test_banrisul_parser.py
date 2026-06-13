from pathlib import Path

from app.connectors.banrisul import BanrisulConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"
SOURCE_URL = "https://www.banrisul.com.br/bob/link/bobw10hn_leiloes_comprar_lista.aspx?secao_id=3551"


def _props():
    raw = (FIXTURES / "banrisul_list.html").read_bytes()
    return list(BanrisulConnector().parse(raw, SOURCE_URL))


def test_banrisul_extracts_rows():
    props = _props()
    assert len(props) >= 1
    assert all(p.bank_code == "banrisul" for p in props)


def test_banrisul_external_code():
    props = _props()
    # External code is derived from licitação number (e.g., "0013007_2026")
    assert props[0].external_code != ""
    assert "_" in props[0].external_code or "/" in props[0].external_code or props[0].external_code.isdigit()


def test_banrisul_has_auction_date():
    props = _props()
    # Every real row should have an abertura (auction opening) date
    assert any(p.raw_data.get("auction_date") for p in props)


def test_banrisul_has_detail_url():
    props = _props()
    for p in props:
        url = p.raw_data.get("official_url", "")
        assert "banrisul.com.br" in url


def test_banrisul_normalize_state_rs():
    norm = BanrisulConnector().normalize(_props()[0])
    assert norm["bank_code"] == "banrisul"
    assert norm["state"] == "RS"
    assert norm["status"] == "active"
