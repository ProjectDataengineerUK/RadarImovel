"""Unit tests for AT-008: Kaplan-Meier heuristic price drop predictions."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from app.prediction.price_drop import (
    _get_prior,
    _load_priors,
    compute_predictions,
    BOOTSTRAP_N,
    HORIZONS,
    PricePredictionResult,
)


@pytest.fixture
def priors():
    return _load_priors()


class TestGetPrior:
    def test_known_bank_modality(self, priors):
        prob, drop = _get_prior(priors, "caixa", "1º Leilão", 30)
        assert 0 < prob < 1
        assert drop > 0

    def test_known_bank_60d(self, priors):
        prob30, _ = _get_prior(priors, "caixa", "1º Leilão", 30)
        prob60, _ = _get_prior(priors, "caixa", "1º Leilão", 60)
        assert prob60 > prob30

    def test_known_bank_90d_highest(self, priors):
        prob60, _ = _get_prior(priors, "caixa", "1º Leilão", 60)
        prob90, _ = _get_prior(priors, "caixa", "1º Leilão", 90)
        assert prob90 >= prob60

    def test_unknown_bank_uses_default(self, priors):
        prob, drop = _get_prior(priors, "unknown_bank", "Unknown Modality", 30)
        assert 0 < prob < 1
        assert drop > 0

    def test_all_horizons_present(self, priors):
        for h in HORIZONS:
            prob, drop = _get_prior(priors, "caixa", "1º Leilão", h)
            assert isinstance(prob, float)
            assert isinstance(drop, float)


class TestBlending:
    def _make_prop(self, bank_code="caixa", modality="1º Leilão"):
        prop = MagicMock()
        prop.id = "prop-001"
        prop.bank = MagicMock()
        prop.bank.code = bank_code
        prop.sale_modality = modality
        prop.status = "active"
        return prop

    def test_no_empirical_data_uses_prior_only(self, priors):
        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = []

        prop = self._make_prop()

        with patch("app.prediction.price_drop._empirical_stats", return_value=(0, None, None)):
            results = compute_predictions(session, prop)

        assert len(results) == len(HORIZONS)
        for r in results:
            assert isinstance(r, PricePredictionResult)
            assert r.basis["blend_weight"] == 0.0

    def test_full_empirical_overrides_prior(self):
        session = MagicMock()
        prop = MagicMock()
        prop.id = "prop-002"
        prop.bank = MagicMock()
        prop.bank.code = "caixa"
        prop.sale_modality = "1º Leilão"
        prop.status = "active"

        with patch(
            "app.prediction.price_drop._empirical_stats",
            return_value=(BOOTSTRAP_N, 0.9, 15.0),
        ):
            results = compute_predictions(session, prop)

        for r in results:
            assert r.basis["blend_weight"] == 1.0
            assert abs(r.probability - 0.9) < 1e-9

    def test_partial_empirical_blends(self):
        session = MagicMock()
        prop = MagicMock()
        prop.id = "prop-003"
        prop.bank = MagicMock()
        prop.bank.code = "caixa"
        prop.sale_modality = "1º Leilão"
        prop.status = "active"

        n = BOOTSTRAP_N // 2
        emp_prob = 0.8

        with patch(
            "app.prediction.price_drop._empirical_stats",
            return_value=(n, emp_prob, 12.0),
        ):
            results = compute_predictions(session, prop)

        priors_data = _load_priors()
        prior_prob, _ = _get_prior(priors_data, "caixa", "1º Leilão", 30)
        expected_w = n / BOOTSTRAP_N
        expected_prob = (1 - expected_w) * prior_prob + expected_w * emp_prob

        r30 = next(r for r in results if r.horizon == 30)
        assert abs(r30.probability - expected_prob) < 1e-6
        assert abs(r30.basis["blend_weight"] - expected_w) < 1e-9

    def test_probability_clamped_0_1(self):
        session = MagicMock()
        prop = MagicMock()
        prop.id = "prop-004"
        prop.bank = MagicMock()
        prop.bank.code = "caixa"
        prop.sale_modality = "1º Leilão"
        prop.status = "active"

        with patch(
            "app.prediction.price_drop._empirical_stats",
            return_value=(BOOTSTRAP_N, 1.5, 50.0),
        ):
            results = compute_predictions(session, prop)

        for r in results:
            assert 0.0 <= r.probability <= 1.0

    def test_result_contains_model_version(self):
        session = MagicMock()
        prop = MagicMock()
        prop.id = "prop-005"
        prop.bank = MagicMock()
        prop.bank.code = "bb"
        prop.sale_modality = "Venda Direta"
        prop.status = "active"

        with patch("app.prediction.price_drop._empirical_stats", return_value=(0, None, None)):
            results = compute_predictions(session, prop)

        for r in results:
            assert r.model_version.startswith("v")
            assert r.property_id == "prop-005"
