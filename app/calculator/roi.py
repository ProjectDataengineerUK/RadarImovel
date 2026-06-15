"""Calculadora de retorno financeiro para imóveis em leilão."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from app.core.logging import logger

Intention = Literal["revenda", "aluguel", "moradia"]

_ITBI_REGISTRY = Decimal("0.04")
_VACANT_MONTHS = Decimal("1")
_ADMIN_FEE = Decimal("0.08")


@dataclass
class ROIInput:
    lance_value: Decimal
    intention: Intention
    horizon_months: int
    selic_annual: Decimal
    area_sqm: float | None = None
    reform_cost_per_sqm: Decimal = Decimal("500")
    market_price_per_sqm_sale: Decimal | None = None
    market_price_per_sqm_rent: Decimal | None = None


@dataclass
class ROIResult:
    roi_pct: float | None
    yield_annual_pct: float | None
    payback_months: float | None
    cdi_equivalent_pct: float
    net_gain_vs_cdi_pct: float | None
    assumptions: dict = field(default_factory=dict)


def calculate_roi(inp: ROIInput) -> ROIResult:
    area = Decimal(str(inp.area_sqm)) if inp.area_sqm else Decimal("0")
    lance = Decimal(str(inp.lance_value))
    reform_cost = Decimal(str(inp.reform_cost_per_sqm)) if inp.reform_cost_per_sqm is not None else Decimal("0")
    reform_total = area * reform_cost
    total_invested = lance + reform_total

    roi_pct: float | None = None
    yield_annual_pct: float | None = None
    payback_months: float | None = None

    try:
        if inp.intention == "revenda" and inp.market_price_per_sqm_sale and inp.area_sqm:
            sqm_sale = Decimal(str(inp.market_price_per_sqm_sale))
            market_value = area * sqm_sale
            transaction_costs = total_invested * _ITBI_REGISTRY
            net_gain = market_value - total_invested - transaction_costs
            roi_pct = float(net_gain / total_invested * 100)

        elif inp.intention == "aluguel" and inp.market_price_per_sqm_rent and inp.area_sqm:
            sqm_rent = Decimal(str(inp.market_price_per_sqm_rent))
            gross_monthly = area * sqm_rent
            effective_monthly = gross_monthly * (1 - _ADMIN_FEE)
            annual_rent = effective_monthly * (12 - _VACANT_MONTHS)
            yield_annual_pct = float(annual_rent / total_invested * 100)
            if effective_monthly > 0:
                payback_months = float(total_invested / effective_monthly)
    except Exception as exc:
        logger.warning("roi.calculation_error", error=str(exc))

    selic = Decimal(str(inp.selic_annual))
    cdi_pct = float(selic * inp.horizon_months / 12 * 100)
    comparable = roi_pct if roi_pct is not None else yield_annual_pct
    net_gain_vs_cdi = (comparable - cdi_pct) if comparable is not None else None

    return ROIResult(
        roi_pct=roi_pct,
        yield_annual_pct=yield_annual_pct,
        payback_months=payback_months,
        cdi_equivalent_pct=cdi_pct,
        net_gain_vs_cdi_pct=net_gain_vs_cdi,
        assumptions={
            "total_invested": float(total_invested),
            "reform_total": float(reform_total),
            "itbi_registry_pct": float(_ITBI_REGISTRY * 100),
            "selic_annual_pct": float(inp.selic_annual * 100),
            "horizon_months": inp.horizon_months,
        },
    )
