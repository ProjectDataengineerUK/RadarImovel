from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.agents.score_agent import calculate_enriched_score, calculate_score


@pytest.fixture(autouse=True)
def mock_settings():
    settings = MagicMock()
    settings.score_discount_max_points = 60
    settings.score_occupancy_bonus = 40
    settings.score_discount_enriched_max = 45
    settings.score_occupancy_enriched_max = 20
    settings.score_payment_max = 10
    settings.score_proximity_max = 5
    settings.score_debt_penalty_max = 30
    settings.score_risk_flag_penalty = 7
    settings.score_risk_flag_penalty_max = 20
    settings.score_onus_penalty = 15
    with patch("app.agents.score_agent.get_settings", return_value=settings):
        yield


def _property():
    return {
        "discount_percent": 40,
        "occupancy_status": "Desocupado",
        "appraisal_value": 200000,
        "minimum_value": 120000,
        "current_value": 120000,
    }


def _ocupado_property():
    """Score básico baixo: ocupado, desconto modesto."""
    return {
        "discount_percent": 20,
        "occupancy_status": "Ocupado",
        "appraisal_value": 200000,
        "minimum_value": 100000,
        "current_value": 100000,
    }


def test_score_livre_sem_divida():
    in_window = (datetime.now().date() + timedelta(days=25)).isoformat()
    extraction = {
        "occupancy_detail": "livre",
        "total_debt_estimate": 0,
        "appraisal_value": 200000,
        "minimum_bid_1st": 100000,
        "payment_modalities": ["vista", "financiamento_caixa", "fgts"],
        "encumbrances": [],
        "risk_flags": [],
        "risk_level": "low",
        "auction_date_1st": in_window,
        "extraction_confidence": 0.9,
    }
    prop = _ocupado_property()
    base = calculate_score(prop)
    score, risk = calculate_enriched_score(prop, extraction)
    assert score > base
    assert risk == "low"


def test_score_ocupado_divida_alta():
    extraction = {
        "occupancy_detail": "ocupado_com_acao_judicial",
        "total_debt_estimate": 50000,
        "appraisal_value": 200000,
        "minimum_bid_1st": 120000,
        "payment_modalities": ["vista"],
        "encumbrances": [{"type": "hipoteca", "amount_approx": None}],
        "risk_flags": ["ocupado", "divida_elevada", "onus_registrado"],
        "risk_level": "high",
        "extraction_confidence": 0.85,
    }
    base = calculate_score(_property())
    score, risk = calculate_enriched_score(_property(), extraction)
    assert score < base
    assert risk == "high"


def test_score_sem_extracao():
    p = _property()
    score, risk = calculate_enriched_score(p, None)
    assert score == calculate_score(p)
    assert risk == "low"


def test_confidence_blending():
    extraction = {
        "occupancy_detail": "ocupado_com_acao_judicial",
        "total_debt_estimate": 50000,
        "appraisal_value": 200000,
        "minimum_bid_1st": 120000,
        "payment_modalities": [],
        "encumbrances": [],
        "risk_flags": ["divida_elevada"],
        "risk_level": "high",
        "extraction_confidence": 0.4,
    }
    base = calculate_score(_property())
    score, _ = calculate_enriched_score(_property(), extraction)
    low = min(base, score)
    high = max(base, score)
    assert low <= score <= high


def test_debt_ratio_threshold_high_risk():
    extraction = {
        "occupancy_detail": "livre",
        "total_debt_estimate": 60000,
        "appraisal_value": 200000,
        "minimum_bid_1st": 120000,
        "payment_modalities": [],
        "encumbrances": [],
        "risk_flags": ["divida_elevada"],
        "risk_level": "high",
        "extraction_confidence": 0.9,
    }
    _, risk = calculate_enriched_score(_property(), extraction)
    assert risk == "high"


def test_score_clamped_0_100():
    extraction = {
        "occupancy_detail": "ocupado_com_acao_judicial",
        "total_debt_estimate": 500000,
        "appraisal_value": 200000,
        "minimum_bid_1st": 200000,
        "payment_modalities": [],
        "encumbrances": [{"type": "hipoteca"}],
        "risk_flags": ["ocupado", "divida_elevada", "onus_registrado", "leilao_judicial"],
        "risk_level": "high",
        "extraction_confidence": 1.0,
    }
    score, _ = calculate_enriched_score(_property(), extraction)
    assert 0 <= score <= 100
