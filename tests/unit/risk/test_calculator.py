"""Unit tests for app/risk/calculator.py — weights, classification, score_partial."""
from unittest.mock import MagicMock, patch

import pytest

from app.risk.schemas import DimensionScore, RiskIndicator


def _make_dim(code: str, raw_points: float, partial: bool = False) -> DimensionScore:
    return DimensionScore(code=code, name=code.lower(), raw_points=raw_points, indicators=[], partial=partial)


@pytest.mark.parametrize(
    "score,expected",
    [
        (0, "low"),
        (20, "low"),
        (21, "moderate"),
        (40, "moderate"),
        (41, "elevated"),
        (60, "elevated"),
        (61, "high"),
        (80, "high"),
        (81, "critical"),
        (100, "critical"),
    ],
)
def test_classify(score, expected):
    from app.risk.calculator import _classify
    assert _classify(score) == expected


def test_weights_sum_to_one():
    from app.risk.calculator import _WEIGHTS
    assert abs(sum(_WEIGHTS.values()) - 1.0) < 1e-9


def test_calculate_risk_integration(tmp_path):
    """calculate_risk returns correct weighted score with all mocked sources."""
    from app.risk.calculator import calculate_risk

    prop = MagicMock()
    prop.id = "00000000-0000-0000-0000-000000000001"
    prop.address = "Rua A, 100"
    prop.city = "São Paulo"
    prop.state = "SP"
    prop.latitude = -23.55
    prop.longitude = -46.60
    prop.occupancy_status = "livre"
    prop.current_value = 300_000
    prop.area_total = 100
    prop.appraisal_value = 400_000
    prop.zipcode = "01310-100"
    prop.ibge_code = None
    prop.edital_url = None

    session = MagicMock()
    session.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = None

    with (
        patch("app.risk.calculator.CnjClient") as MockCnj,
        patch("app.risk.calculator.IbamaLookup") as MockIbama,
        patch("app.risk.calculator.CemadenLookup") as MockCemaden,
        patch("app.risk.calculator.TransparenciaClient") as MockTransp,
        patch("app.risk.calculator.IbgeLookup") as MockIbge,
        patch("app.risk.calculator.IpeaAtlas") as MockIpea,
        patch("app.risk.calculator.ReceitaClient") as MockReceita,
        patch("app.risk.calculator.FipeClient") as MockFipe,
    ):
        MockCnj.return_value.search.return_value = []
        MockIbama.return_value.contains_point.return_value = []
        MockCemaden.return_value.risk_zones.return_value = []
        MockTransp.return_value.get_iptu_debt.return_value = None
        MockIbge.return_value.get_stats.return_value = None
        MockIpea.return_value.get_homicide_rate.return_value = None
        MockReceita.return_value.get_cnpj.return_value = None
        MockFipe.return_value.get_price_per_sqm.return_value = None

        result = calculate_risk(prop, session)

    assert result.score_total == 0.0
    assert result.risk_level == "low"
    assert result.score_partial  # sources unavailable (transp=None, ibge_code=None, fipe=None)
    assert result.calculation_version == "1.0"


def test_score_partial_when_cnj_fails():
    from app.risk.dimensions.juridico import score_juridico

    class FailingCnj:
        def search(self, **kwargs):
            raise RuntimeError("timeout")

    dim = score_juridico(
        cnpj_owner=None,
        address="Rua A",
        city="SP",
        state="SP",
        cnj_client=FailingCnj(),
    )
    assert dim.partial is True
    assert dim.raw_points == 0.0
