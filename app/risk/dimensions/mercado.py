"""Dimensão F — Mercado: preço/m² vs mercado (fonte opcional, falha silenciosa)."""
from datetime import date
from decimal import Decimal

from app.risk.schemas import DimensionScore, RiskIndicator
from app.risk.sources.fipe import FipeClient


def score_mercado(
    city: str,
    state: str,
    current_value: Decimal | float | None,
    area_total: Decimal | float | None,
    fipe: FipeClient,
) -> DimensionScore:
    if not current_value or not area_total or float(area_total) <= 0:
        return DimensionScore(code="F", name="mercado", raw_points=0.0, indicators=[], partial=True)

    market_price = fipe.get_price_per_sqm(city, state)
    if market_price is None:
        return DimensionScore(code="F", name="mercado", raw_points=0.0, indicators=[], partial=True)

    property_price_sqm = float(current_value) / float(area_total)
    ratio = property_price_sqm / market_price if market_price > 0 else 1.0

    if ratio > 1.30:
        points = 40
        note = f"acima do mercado em {ratio - 1:.0%}"
    elif ratio > 1.10:
        points = 20
        note = f"levemente acima do mercado ({ratio:.2f}x)"
    else:
        points = 0
        note = f"alinhado/abaixo do mercado ({ratio:.2f}x)"

    return DimensionScore(
        code="F",
        name="mercado",
        raw_points=points,
        indicators=[
            RiskIndicator(
                code="F1",
                value=round(ratio, 3),
                source="Fipe ZAP / ZAP Imóveis",
                date_fetched=date.today(),
                note=note,
            )
        ],
        partial=False,
    )
