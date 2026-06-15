"""Tests for SuperleiloesParser."""
import json
import pytest
from app.connectors.superleiloes.parser import SuperleiloesParser


@pytest.fixture
def parser():
    return SuperleiloesParser()


def test_parse_json_list(parser):
    payload = json.dumps([
        {
            "id": "42",
            "titulo": "Apartamento em São Paulo",
            "cidade": "São Paulo",
            "uf": "SP",
            "valorInicial": 200000,
            "valorAvaliacao": 350000,
            "url": "/lote/42",
        }
    ]).encode()
    results = list(parser.parse(payload, "https://superleiloes.com.br/lotes/imoveis"))
    assert len(results) == 1
    raw = results[0]
    assert raw.external_code == "42"
    assert raw.raw_data["city"] == "São Paulo"
    assert raw.raw_data["state"] == "SP"
    assert raw.raw_data["current_value"] == "200000"


def test_parse_empty(parser):
    assert list(parser.parse(b"", "url")) == []


def test_parse_invalid_json(parser):
    assert list(parser.parse(b"not json", "url")) == []


def test_parse_json_with_items_key(parser):
    payload = json.dumps({"items": [
        {"id": "5", "titulo": "Casa RJ", "cidade": "Rio", "uf": "RJ", "valorInicial": 100000},
    ]}).encode()
    results = list(parser.parse(payload, "url"))
    assert len(results) == 1
    assert results[0].raw_data["state"] == "RJ"


def test_parse_html_fallback(parser):
    html = b"""
    <html><body>
    <div class="lote-card" data-lote-id="7">
        <h2 class="titulo">Sala Comercial</h2>
        <span class="localizacao">Curitiba/PR</span>
        <span class="lance-inicial">R$ 80.000</span>
    </div>
    </body></html>
    """
    results = list(parser.parse(html, "https://superleiloes.com.br"))
    assert len(results) == 1
