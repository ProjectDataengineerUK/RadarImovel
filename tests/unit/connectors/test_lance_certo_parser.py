"""Tests for LanceCertoParser."""
import pytest
from bs4 import BeautifulSoup
from app.connectors.lance_certo.parser import LanceCertoParser


@pytest.fixture
def parser():
    return LanceCertoParser()


def _make_html(title="Aparmento SP", price="R$ 150.000", city_state="São Paulo/SP", lot_id="999"):
    return f"""
    <html><body>
    <div class="auction-item" data-lote-id="{lot_id}">
        <h2 class="title">{title}</h2>
        <span class="location">{city_state}</span>
        <span class="price">{price}</span>
        <a href="/lote/{lot_id}">Ver</a>
    </div>
    </body></html>
    """.encode()


def test_parse_basic_item(parser):
    html = _make_html()
    results = list(parser.parse(html, "https://lancecerto.com.br/imoveis"))
    assert len(results) == 1
    raw = results[0]
    assert raw.external_code == "999"
    assert raw.raw_data["city"] == "São Paulo"
    assert raw.raw_data["state"] == "SP"


def test_parse_empty_bytes(parser):
    assert list(parser.parse(b"", "https://lancecerto.com.br")) == []


def test_parse_no_items(parser):
    html = b"<html><body><p>Nada</p></body></html>"
    results = list(parser.parse(html, "https://lancecerto.com.br"))
    assert results == []


def test_parse_multiple_items(parser):
    html = """
    <html><body>
    <div class="auction-item" data-lote-id="1"><h2 class="title">Casa</h2><span class="location">Campinas/SP</span></div>
    <div class="auction-item" data-lote-id="2"><h2 class="title">Apto</h2><span class="location">Rio/RJ</span></div>
    </body></html>
    """.encode()
    results = list(parser.parse(html, "https://lancecerto.com.br"))
    assert len(results) == 2
