"""Dimensão C — Fiscal: IPTU + dívida ativa municipal."""
from datetime import date
from decimal import Decimal

from app.risk.schemas import DimensionScore, RiskIndicator
from app.risk.sources.transparencia import TransparenciaClient


def score_fiscal(
    address: str,
    city: str,
    state: str,
    appraisal_value: Decimal | float | None,
    zipcode: str | None,
    transparencia: TransparenciaClient,
    settings=None,
) -> DimensionScore:
    indicators: list[RiskIndicator] = []
    points = 0.0
    partial = False

    if not settings:
        from app.core.config import get_settings
        settings = get_settings()

    try:
        result = transparencia.get_iptu_debt(
            address=address,
            city=city,
            state=state,
            zipcode=zipcode,
        )
    except Exception:
        partial = True
        result = None

    if result is None:
        partial = True
    elif result.get("has_debt"):
        debt_ratio = result.get("debt_ratio")
        if debt_ratio is not None:
            high_threshold: float = settings.risk_iptu_debt_ratio_high
            if debt_ratio >= high_threshold:
                points = 60
            else:
                points = 30
            indicators.append(
                RiskIndicator(
                    code="C1",
                    value=round(debt_ratio, 3),
                    source="Portal de Transparência Municipal",
                    date_fetched=date.today(),
                    note=f"dívida IPTU: {debt_ratio:.1%} do valor venal",
                )
            )
        else:
            points = 20
            indicators.append(
                RiskIndicator(
                    code="C1",
                    value=True,
                    source="Portal de Transparência Municipal",
                    date_fetched=date.today(),
                    note="dívida ativa detectada (valor não disponível)",
                )
            )

    return DimensionScore(
        code="C",
        name="fiscal",
        raw_points=min(points, 100),
        indicators=indicators,
        partial=partial,
    )
