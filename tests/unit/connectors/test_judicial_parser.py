"""Tests for JudicialParser."""
import json
import pytest
from app.connectors.judicial.parser import JudicialParser


@pytest.fixture
def parser():
    return JudicialParser(tribunal="TRT2")


def test_parse_single_hit(parser):
    payload = json.dumps([
        {
            "process_number": "1234567-00.2024.5.02.0001",
            "summary": "Hasta Pública — Imóvel Residencial",
            "city": "São Paulo",
            "state": "SP",
            "minimum_value": "180000.00",
            "hasta_date": "2024-08-10",
            "auctioneer": "Dr. João Silva",
            "process_url": "https://cnj.jus.br/processo/1234567",
        }
    ]).encode()

    results = list(parser.parse(payload, "TRT2:0"))
    assert len(results) == 1
    raw = results[0]
    assert raw.external_code == "1234567-00.2024.5.02.0001"
    assert raw.bank_code == "judicial_trt"
    assert raw.raw_data["city"] == "São Paulo"
    assert raw.raw_data["process_number"] == "1234567-00.2024.5.02.0001"


def test_parse_empty_bytes(parser):
    assert list(parser.parse(b"", "TRT2:0")) == []


def test_parse_invalid_json(parser):
    assert list(parser.parse(b"not json", "TRT2:0")) == []


def test_skip_hit_without_process_number(parser):
    payload = json.dumps([{"summary": "Hasta", "city": "Rio", "state": "RJ"}]).encode()
    assert list(parser.parse(payload, "TRT2:0")) == []


def test_parse_multiple_hits(parser):
    payload = json.dumps([
        {"process_number": "0001", "city": "SP", "state": "SP"},
        {"process_number": "0002", "city": "RJ", "state": "RJ"},
    ]).encode()
    results = list(parser.parse(payload, "TRT2:0"))
    assert len(results) == 2
