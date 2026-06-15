"""Tests for FipeZapClient."""
from unittest.mock import MagicMock, patch
import pytest
from app.services.fipezap import FipeZapClient, get_market_prices_for_city


@pytest.fixture
def client():
    return FipeZapClient()


def test_fetch_index_returns_list(client):
    mock_rows = [
        {"city": "São Paulo", "uf": "SP", "property_type": "Apartamento", "price_per_sqm": 9500.0},
        {"city": "Rio de Janeiro", "uf": "RJ", "property_type": "Apartamento", "price_per_sqm": 7200.0},
    ]
    with patch.object(client, "fetch_index", return_value=mock_rows):
        result = client.fetch_index("2026-06")
    assert len(result) == 2
    assert result[0]["city"] == "São Paulo"


def test_fetch_index_handles_empty(client):
    with patch.object(client, "fetch_index", return_value=[]):
        result = client.fetch_index("2026-01")
    assert result == []


def test_get_market_prices_for_city_returns_row():
    mock_session = MagicMock()
    mock_row = MagicMock()
    mock_row.price_per_sqm_sale = 9500.0
    mock_session.execute.return_value.fetchone.return_value = mock_row

    row = get_market_prices_for_city("São Paulo", "SP", "Apartamento", mock_session)
    assert row is not None


def test_get_market_prices_returns_none_when_not_found():
    mock_session = MagicMock()
    mock_session.execute.return_value.fetchone.return_value = None

    row = get_market_prices_for_city("Cidade Inexistente", "XX", "Apartamento", mock_session)
    assert row is None
