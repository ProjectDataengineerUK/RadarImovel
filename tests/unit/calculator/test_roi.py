"""Tests for ROI calculator."""
import pytest
from app.calculator.roi import ROIInput, ROIResult, calculate_roi


def _base_input(**kwargs) -> ROIInput:
    defaults = dict(
        lance_value=300_000.0,
        intention="revenda",
        horizon_months=60,
        selic_annual=0.105,  # decimal fraction (10.5%)
        area_sqm=80.0,
        reform_cost_per_sqm=500.0,
        market_price_per_sqm_sale=5000.0,
        market_price_per_sqm_rent=None,
    )
    defaults.update(kwargs)
    return ROIInput(**defaults)


def test_revenda_roi_positive_when_below_market():
    inp = _base_input(lance_value=200_000.0, market_price_per_sqm_sale=4000.0, area_sqm=80.0)
    result = calculate_roi(inp)
    assert isinstance(result, ROIResult)
    assert result.roi_pct > 0


def test_roi_beats_cdi_when_large_discount():
    inp = _base_input(lance_value=150_000.0, market_price_per_sqm_sale=5000.0, area_sqm=80.0)
    result = calculate_roi(inp)
    assert result.net_gain_vs_cdi_pct > 0


def test_aluguel_intention_returns_yield():
    inp = _base_input(
        intention="aluguel",
        market_price_per_sqm_rent=25.0,
        area_sqm=80.0,
    )
    result = calculate_roi(inp)
    assert result.yield_annual_pct is not None
    assert result.yield_annual_pct > 0


def test_moradia_intention_no_yield():
    inp = _base_input(intention="moradia")
    result = calculate_roi(inp)
    assert result.yield_annual_pct is None


def test_assumptions_populated():
    inp = _base_input()
    result = calculate_roi(inp)
    assert "total_invested" in result.assumptions
    assert "horizon_months" in result.assumptions


def test_roi_with_no_market_price():
    inp = _base_input(market_price_per_sqm_sale=None)
    result = calculate_roi(inp)
    # Without market price, roi_pct is None but result is valid
    assert isinstance(result, ROIResult)
    assert result.cdi_equivalent_pct >= 0
