"""AT-006: Calculadora de viabilidade financeira (unit tests)."""
import pytest
from app.calculator.engine import calculate_viability, _irr, _npv, _acquisition_costs


# ── helpers ───────────────────────────────────────────────────────────────────

def test_acquisition_costs_sp():
    costs = {"itbi_pct": 3.0, "registro_pct": 0.4, "escritura_pct": 0.35}
    total = _acquisition_costs(200_000.0, costs)
    assert abs(total - (6_000 + 800 + 700)) < 0.01


def test_irr_simple_payback():
    # Investimento de 100, retorno de 50/ano por 3 anos → TIR ~23%
    cfs = [-100, 50, 50, 50]
    irr = _irr(cfs)
    assert irr is not None
    assert 0.20 < irr < 0.30


def test_irr_no_return():
    # Projeto sem retorno → deve retornar None ou valor negativo
    result = _irr([-100, 0, 0, 0])
    # Newton-Raphson pode não convergir ou retornar -1
    assert result is None or result < 0


def test_npv_positive():
    # Investimento de 100, fluxo de 40/ano por 3 anos, taxa 10%
    cfs = [-100, 40, 40, 40]
    npv = _npv(0.10 / 12, cfs)
    assert npv > 0


def test_npv_negative():
    # Investimento de 200, fluxo de 10/ano por 3 anos, taxa 12%
    cfs = [-200, 10, 10, 10]
    npv = _npv(0.12 / 12, cfs)
    assert npv < 0


# ── calculate_viability ────────────────────────────────────────────────────────

def test_calculate_viability_returns_two_scenarios():
    results = calculate_viability(
        purchase_price=100_000,
        appraisal_value=140_000,
        state="SP",
    )
    assert len(results) == 2
    scenarios = {r.scenario for r in results}
    assert scenarios == {"venda", "aluguel"}


def test_calculate_viability_venda_viable():
    results = calculate_viability(
        purchase_price=100_000,
        appraisal_value=200_000,  # grande desconto → viável
        state="SP",
    )
    venda = next(r for r in results if r.scenario == "venda")
    assert venda.viable is True
    assert venda.roi_pct > 0
    assert venda.total_investment > 100_000  # inclui custos


def test_calculate_viability_aluguel_yield():
    results = calculate_viability(
        purchase_price=150_000,
        appraisal_value=200_000,
        state="RJ",
        hold_years=5,
    )
    aluguel = next(r for r in results if r.scenario == "aluguel")
    assert aluguel.monthly_rent > 0
    assert aluguel.annual_gross_yield_pct > 0


def test_high_debt_warning():
    results = calculate_viability(
        purchase_price=100_000,
        appraisal_value=130_000,
        state="MG",
        existing_debt=50_000,  # > 30% → warning
    )
    for r in results:
        assert "dívida_herdada_elevada" in r.warnings


def test_no_debt_no_warning():
    results = calculate_viability(
        purchase_price=100_000,
        appraisal_value=130_000,
        state="SC",
        existing_debt=0,
    )
    for r in results:
        assert "dívida_herdada_elevada" not in r.warnings


def test_unknown_state_uses_defaults():
    # Estado inexistente cai no default
    results = calculate_viability(
        purchase_price=80_000,
        appraisal_value=100_000,
        state="XX",  # inválido
    )
    assert len(results) == 2
    for r in results:
        assert r.acquisition_costs > 0


def test_discount_vs_appraisal():
    results = calculate_viability(
        purchase_price=70_000,
        appraisal_value=100_000,
        state="GO",
    )
    for r in results:
        # 30% de desconto esperado
        assert abs(r.discount_vs_appraisal_pct - 30.0) < 1.0
