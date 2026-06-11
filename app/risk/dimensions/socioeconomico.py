"""Dimensão E — Socioeconômico: IDH, homicídios, vacância, crescimento pop."""
from datetime import date

from app.risk.schemas import DimensionScore, RiskIndicator
from app.risk.sources.ibge import IbgeLookup
from app.risk.sources.ipea import IpeaAtlas


def score_socioeconomico(
    ibge_code: str | None,
    ibge: IbgeLookup,
    ipea: IpeaAtlas,
    settings=None,
) -> DimensionScore:
    indicators: list[RiskIndicator] = []
    points = 0.0
    partial = ibge_code is None

    if not settings:
        from app.core.config import get_settings
        settings = get_settings()

    if not ibge_code:
        return DimensionScore(code="E", name="socioeconomico", raw_points=0.0, indicators=[], partial=True)

    stats = ibge.get_stats(ibge_code)
    homicide_rate = ipea.get_homicide_rate(ibge_code)

    if stats is None and homicide_rate is None:
        partial = True
        return DimensionScore(code="E", name="socioeconomico", raw_points=0.0, indicators=[], partial=True)

    if stats:
        idh = stats.get("idh")
        if idh is not None:
            if idh < settings.risk_idh_threshold_low:
                points += 30
                label = "baixo"
            elif idh < settings.risk_idh_threshold_medium:
                points += 15
                label = "médio"
            else:
                label = "alto"
            indicators.append(
                RiskIndicator(
                    code="E1",
                    value=round(idh, 3),
                    source="IBGE Censo 2022",
                    date_fetched=date.today(),
                    note=f"IDH municipal: {label}",
                )
            )

        pop_2022 = stats.get("population_2022")
        pop_2010 = stats.get("population_2010")
        if pop_2022 and pop_2010 and pop_2010 > 0:
            growth = (pop_2022 - pop_2010) / pop_2010
            if growth < -settings.risk_pop_decline_threshold:
                points += 15
                indicators.append(
                    RiskIndicator(
                        code="E2",
                        value=round(growth, 3),
                        source="IBGE Censo 2022",
                        date_fetched=date.today(),
                        note=f"declínio populacional: {growth:.1%}",
                    )
                )

        vacancy = stats.get("vacancy_rate")
        if vacancy is not None and vacancy > 0.20:
            points += 10
            indicators.append(
                RiskIndicator(
                    code="E3",
                    value=round(vacancy, 3),
                    source="IBGE Censo 2022",
                    date_fetched=date.today(),
                    note=f"taxa de vacância: {vacancy:.1%}",
                )
            )

    if homicide_rate is not None:
        high_threshold: int = settings.risk_homicide_threshold_high
        medium_threshold: int = settings.risk_homicide_threshold_medium
        if homicide_rate >= high_threshold:
            points += 25
            label = "alto"
        elif homicide_rate >= medium_threshold:
            points += 12
            label = "médio"
        else:
            label = "baixo"
        indicators.append(
            RiskIndicator(
                code="E4",
                value=round(homicide_rate, 1),
                source="IPEA Atlas da Violência",
                date_fetched=date.today(),
                note=f"homicídios/100k hab: {label}",
            )
        )

    return DimensionScore(
        code="E",
        name="socioeconomico",
        raw_points=min(points, 100),
        indicators=indicators,
        partial=partial,
    )
