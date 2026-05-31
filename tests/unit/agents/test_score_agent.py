import pytest
from unittest.mock import patch, MagicMock
from app.agents.score_agent import calculate_score


@pytest.fixture(autouse=True)
def mock_settings():
    settings = MagicMock()
    settings.score_discount_max_points = 60
    settings.score_occupancy_bonus = 40
    with patch("app.agents.score_agent.get_settings", return_value=settings):
        yield


def test_desocupado_max_desconto():
    score = calculate_score({"discount_percent": 60, "occupancy_status": "Desocupado"})
    assert score == 100


def test_desocupado_sem_desconto():
    score = calculate_score({"discount_percent": 0, "occupancy_status": "Desocupado"})
    assert score == 40


def test_ocupado_com_desconto():
    score = calculate_score({"discount_percent": 30, "occupancy_status": "Ocupado"})
    assert score == 30


def test_desconto_acima_do_maximo_eh_clamped():
    score = calculate_score({"discount_percent": 80, "occupancy_status": "Ocupado"})
    assert score == 60


def test_score_maximo_eh_100():
    score = calculate_score({"discount_percent": 90, "occupancy_status": "Desocupado"})
    assert score == 100


def test_desconto_none_retorna_ocupancy_bonus():
    score = calculate_score({"discount_percent": None, "occupancy_status": "Desocupado"})
    assert score == 40


def test_dados_vazios():
    score = calculate_score({})
    assert score == 0
