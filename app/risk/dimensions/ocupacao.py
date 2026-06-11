"""Dimensão D — Ocupação: dados do edital (Fase 2) + CNPJ no endereço."""
from datetime import date

from app.risk.schemas import DimensionScore, RiskIndicator
from app.risk.sources.receita import ReceitaClient

_OCUPADO_KEYWORDS = {"ocupado", "ocupação irregular", "invasão", "posseiro"}


def score_ocupacao(
    occupancy_status: str,
    address: str,
    city: str,
    state: str,
    cnpj_at_address: str | None,
    ai_summary: dict | None,
    receita: ReceitaClient,
    settings=None,
) -> DimensionScore:
    indicators: list[RiskIndicator] = []
    points = 0.0

    if not settings:
        from app.core.config import get_settings
        settings = get_settings()

    if any(kw in occupancy_status.lower() for kw in _OCUPADO_KEYWORDS):
        points += 40
        indicators.append(
            RiskIndicator(
                code="D1",
                value=occupancy_status,
                source="Dados da Caixa / Edital",
                date_fetched=date.today(),
                note="imóvel com ocupação irregular",
            )
        )

    if ai_summary:
        risk_flags: list[str] = ai_summary.get("risk_flags", [])
        onus: list[str] = ai_summary.get("encumbrances", [])
        if risk_flags:
            penalty = min(len(risk_flags) * settings.score_risk_flag_penalty, settings.score_risk_flag_penalty_max)
            points += penalty
            indicators.append(
                RiskIndicator(
                    code="D2",
                    value=risk_flags,
                    source="Gemini — extração de edital",
                    date_fetched=date.today(),
                )
            )
        if onus:
            points += settings.score_onus_penalty
            indicators.append(
                RiskIndicator(
                    code="D3",
                    value=len(onus),
                    source="Gemini — extração de edital",
                    date_fetched=date.today(),
                    note="ônus/gravames identificados no edital",
                )
            )

    if cnpj_at_address:
        cnpj_data = receita.get_cnpj(cnpj_at_address)
        if cnpj_data and cnpj_data.get("ativa"):
            points += settings.risk_cnpj_address_penalty
            indicators.append(
                RiskIndicator(
                    code="D4",
                    value=cnpj_data["razao_social"],
                    source="Receita Federal CNPJ",
                    date_fetched=date.today(),
                    note="CNPJ ativo registrado no endereço",
                )
            )

    return DimensionScore(
        code="D",
        name="ocupacao",
        raw_points=min(points, 100),
        indicators=indicators,
        partial=False,
    )
