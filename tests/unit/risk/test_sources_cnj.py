"""Unit tests for CNJ Datajud client — happy path, 429, timeout, fallback."""
import json
from unittest.mock import patch

import httpx
import pytest

from app.risk.sources.cnj import CnjClient


def _make_response(hits, status_code=200):
    content = json.dumps({"hits": {"hits": hits}})
    req = httpx.Request("GET", "https://api-publica.datajud.cnj.jus.br/api_publica/processo")
    return httpx.Response(status_code, text=content, request=req)


CNJ_HIT = {
    "_source": {
        "numeroProcesso": "0001234-55.2020.8.26.0100",
        "classe": {"nome": "Execução Fiscal"},
        "tribunal": "TJSP",
        "movimentos": [{"nome": "Distribuição"}],
    }
}


def test_search_by_cnpj_happy_path():
    client = CnjClient(timeout=5)
    with patch("httpx.get", return_value=_make_response([CNJ_HIT])):
        results = client.search(cnpj="12345678000100", address="", city="SP", state="SP")
    assert len(results) == 1
    assert results[0]["classe"] == "Execução Fiscal"


def test_search_returns_empty_on_http_error():
    client = CnjClient(timeout=5)
    with patch("httpx.get", side_effect=httpx.HTTPStatusError("429", request=None, response=httpx.Response(429))):
        results = client.search(cnpj="12345678000100", address="", city="SP", state="SP")
    assert results == []


def test_search_returns_empty_on_timeout():
    client = CnjClient(timeout=5)
    with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
        results = client.search(cnpj="12345678000100", address="", city="SP", state="SP")
    assert results == []


def test_fallback_to_address_when_cnpj_returns_empty():
    client = CnjClient(timeout=5)
    address_hit = {
        "_source": {
            "numeroProcesso": "9999999-00.2021.8.26.0100",
            "classe": {"nome": "Inventário"},
            "tribunal": "TJSP",
            "movimentos": [{"nome": "Petição"}],
        }
    }
    responses = [
        _make_response([]),          # cnpj search — empty
        _make_response([address_hit]),  # address fallback
    ]
    with patch("httpx.get", side_effect=responses):
        results = client.search(cnpj="12345678000100", address="Rua A, 100", city="SP", state="SP")
    assert len(results) == 1
    assert results[0]["classe"] == "Inventário"


def test_no_cnpj_goes_directly_to_address():
    client = CnjClient(timeout=5)
    with patch("httpx.get", return_value=_make_response([CNJ_HIT])):
        results = client.search(cnpj=None, address="Rua A", city="SP", state="SP")
    assert len(results) == 1
