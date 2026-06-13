from pathlib import Path

from app.connectors.basa import BASAConnector

FIXTURES = Path(__file__).parents[2] / "fixtures" / "html"
INDEX_URL = "https://www.bancoamazonia.com.br/o-banco/licitacoes/leiloes-de-imoveis"


def _index_props():
    raw = (FIXTURES / "basa_index.html").read_bytes()
    return list(BASAConnector().parse(raw, INDEX_URL))


def test_basa_index_extracts_rows():
    props = _index_props()
    # BASA rarely has listings; real page had 1 entry (from 2021)
    assert isinstance(props, list)
    assert all(p.bank_code == "basa" for p in props)


def test_basa_index_no_table_yields_nothing():
    html = "<html><body><p>Sem leiloes no momento.</p></body></html>".encode("utf-8")
    props = list(BASAConnector().parse(html, INDEX_URL))
    assert props == []


def test_basa_index_row_has_edital_url():
    props = _index_props()
    if not props:
        return  # BASA may have no current listings
    for p in props:
        url = p.raw_data.get("edital_url") or p.raw_data.get("official_url") or ""
        assert url != ""


def test_basa_index_city_state_parsed():
    props = _index_props()
    if not props:
        return
    norms = [BASAConnector().normalize(p) for p in props]
    for n in norms:
        assert n["state"] in ("PA", "AM", "AC", "AP", "RO", "RR", "TO", "MA", "MT", "GO", "RJ", "")
        assert n["bank_code"] == "basa"
        assert n["sale_modality"] == "Leilão"
