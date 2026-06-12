"""Calculadora de viabilidade financeira para imóveis de leilão.

Calcula TIR, VPL, payback e margem de dois cenários: venda rápida e aluguel
com venda futura. Custos (ITBI, registro, escritura) são lidos da tabela
`cost_tables` (admin-editável) com fallback para o YAML de seeds.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from sqlalchemy.orm import Session

_SEEDS_PATH = Path(__file__).parent / "seeds" / "costs_2026.yaml"
_RENOVATION_RATE = 0.10  # 10% do valor de compra como estimativa conservadora
_HOLDING_MONTHS = 12  # meses de manutenção antes da venda
_MONTHLY_CONDO_DEFAULT = 600.0  # R$/mês condomínio estimado se não informado
_RENTAL_YIELD_PA = 0.060  # yield bruto anual de aluguel padrão (6% a.a.)
_DISCOUNT_RATE_PA = 0.12  # WACC/taxa de desconto (Selic + risco; ajustável)


@lru_cache(maxsize=1)
def _load_seed_costs() -> dict:
    with open(_SEEDS_PATH) as f:
        return yaml.safe_load(f)


def _get_state_costs(state: str, db: Session | None = None) -> dict:
    """Retorna {itbi_pct, registro_pct, escritura_pct} para o estado."""
    if db is not None:
        from app.models.cost_table import CostTable
        row = db.query(CostTable).filter_by(state=state.upper(), active=True).first()
        if row:
            return {
                "itbi_pct": float(row.itbi_pct),
                "registro_pct": float(row.registro_pct),
                "escritura_pct": float(row.escritura_pct),
            }

    seeds = _load_seed_costs()
    state_data = seeds.get("states", {}).get(state.upper())
    if state_data:
        return state_data
    return seeds["defaults"]


def _acquisition_costs(purchase_price: float, costs: dict) -> float:
    itbi = purchase_price * costs["itbi_pct"] / 100
    registro = purchase_price * costs["registro_pct"] / 100
    escritura = purchase_price * costs["escritura_pct"] / 100
    return itbi + registro + escritura


def _npv(rate_per_period: float, cash_flows: list[float]) -> float:
    """Valor Presente Líquido. cash_flows[0] é o investimento inicial (negativo)."""
    total = 0.0
    for t, cf in enumerate(cash_flows):
        total += cf / (1 + rate_per_period) ** t
    return total


def _irr(cash_flows: list[float], max_iter: int = 1000, tol: float = 1e-7) -> float | None:
    """TIR por Newton-Raphson. Retorna None se não convergir."""
    rate = 0.1
    for _ in range(max_iter):
        npv = sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))
        if abs(npv) < tol:
            return rate
        dnpv = sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cash_flows))
        if dnpv == 0:
            return None
        rate -= npv / dnpv
        if rate <= -1:
            return None
    return None


@dataclass
class ViabilityResult:
    scenario: Literal["venda", "aluguel"]
    purchase_price: float
    acquisition_costs: float
    renovation_cost: float
    total_investment: float

    # Venda
    sale_price_estimate: float = 0.0
    gross_margin_pct: float = 0.0
    holding_costs: float = 0.0
    net_profit: float = 0.0
    roi_pct: float = 0.0
    payback_months: int | None = None

    # Aluguel
    monthly_rent: float = 0.0
    annual_gross_yield_pct: float = 0.0
    annual_net_yield_pct: float = 0.0
    exit_value: float = 0.0  # valor na saída após N anos
    irr_annual_pct: float | None = None
    npv: float = 0.0

    # Risco
    max_price_to_breakeven: float = 0.0
    discount_vs_appraisal_pct: float = 0.0
    viable: bool = True
    warnings: list[str] = field(default_factory=list)


def calculate_viability(
    *,
    purchase_price: float,
    appraisal_value: float | None,
    state: str,
    property_type: str = "apartamento",
    area_m2: float | None = None,
    monthly_condo: float | None = None,
    existing_debt: float = 0.0,
    db: Session | None = None,
    hold_years: int = 5,
) -> list[ViabilityResult]:
    """Retorna dois cenários: [venda_rapida, aluguel_com_saida]."""
    costs = _get_state_costs(state, db)
    acq_costs = _acquisition_costs(purchase_price, costs)
    renovation = purchase_price * _RENOVATION_RATE
    total_inv = purchase_price + acq_costs + renovation + existing_debt

    warnings: list[str] = []
    if existing_debt > purchase_price * 0.30:
        warnings.append("dívida_herdada_elevada")

    appraisal = appraisal_value or purchase_price * 1.2
    discount_pct = max(0.0, (appraisal - purchase_price) / appraisal * 100) if appraisal else 0.0

    # ── Cenário 1: venda rápida (HOLDING_MONTHS) ──────────────────────────────
    holding_condo = (monthly_condo or _MONTHLY_CONDO_DEFAULT) * _HOLDING_MONTHS
    holding_iptu = appraisal * 0.005 / 12 * _HOLDING_MONTHS  # ~0.5% a.a.
    holding_total = holding_condo + holding_iptu

    sale_price = appraisal * 0.90  # 10% abaixo da avaliação para giro rápido
    irrf = sale_price * 0.15  # IRRF sobre lucro imobiliário simplificado
    net_sale = sale_price - irrf
    net_profit_sale = net_sale - total_inv - holding_total
    roi_pct = net_profit_sale / total_inv * 100 if total_inv > 0 else 0.0
    breakeven = total_inv + holding_total + irrf  # preço mínimo de venda

    venda = ViabilityResult(
        scenario="venda",
        purchase_price=purchase_price,
        acquisition_costs=acq_costs,
        renovation_cost=renovation,
        total_investment=total_inv,
        sale_price_estimate=sale_price,
        gross_margin_pct=(sale_price - purchase_price) / purchase_price * 100,
        holding_costs=holding_total,
        net_profit=net_profit_sale,
        roi_pct=roi_pct,
        payback_months=_HOLDING_MONTHS if net_profit_sale > 0 else None,
        max_price_to_breakeven=breakeven,
        discount_vs_appraisal_pct=discount_pct,
        viable=net_profit_sale > 0,
        warnings=warnings.copy(),
    )
    if roi_pct < 5:
        venda.warnings.append("margem_baixa")

    # ── Cenário 2: aluguel + venda após hold_years ────────────────────────────
    monthly_rent = appraisal * _RENTAL_YIELD_PA / 12
    vacancy_rate = 0.08  # 8% vacância
    annual_net_rent = monthly_rent * 12 * (1 - vacancy_rate) - holding_condo / _HOLDING_MONTHS * 12
    gross_yield = monthly_rent * 12 / total_inv * 100
    net_yield = annual_net_rent / total_inv * 100

    appreciation_rate = 0.05  # 5% a.a. nominal
    exit_value = appraisal * (1 + appreciation_rate) ** hold_years

    cash_flows: list[float] = [-total_inv]
    for yr in range(1, hold_years + 1):
        rent_yr = annual_net_rent * (1 + 0.03) ** yr  # reajuste IGPM 3%
        cash_flows.append(rent_yr)
    cash_flows[-1] += exit_value  # venda no último ano

    monthly_dr = (1 + _DISCOUNT_RATE_PA) ** (1 / 12) - 1
    npv_val = _npv(monthly_dr, cash_flows) if False else _npv(_DISCOUNT_RATE_PA / 12, cash_flows)
    irr_raw = _irr(cash_flows)
    irr_annual = ((1 + irr_raw) ** 12 - 1) * 100 if irr_raw is not None else None

    aluguel = ViabilityResult(
        scenario="aluguel",
        purchase_price=purchase_price,
        acquisition_costs=acq_costs,
        renovation_cost=renovation,
        total_investment=total_inv,
        monthly_rent=monthly_rent,
        annual_gross_yield_pct=gross_yield,
        annual_net_yield_pct=net_yield,
        exit_value=exit_value,
        irr_annual_pct=irr_annual,
        npv=npv_val,
        max_price_to_breakeven=breakeven,
        discount_vs_appraisal_pct=discount_pct,
        viable=npv_val > 0,
        warnings=warnings.copy(),
    )
    if net_yield < 4:
        aluguel.warnings.append("yield_baixo")

    return [venda, aluguel]
