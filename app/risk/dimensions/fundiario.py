"""Dimensão B — Fundiário: PostGIS spatial join APP/APA/CEMADEN/TI."""
from datetime import date

from app.risk.schemas import DimensionScore, RiskIndicator
from app.risk.sources.cemaden import CemadenLookup
from app.risk.sources.ibama import IbamaLookup

_LAYER_PENALTY = {"APP": 50, "APA": 20, "TI": 60, "UC": 30}


def score_fundiario(
    lat: float | None,
    lng: float | None,
    ibge_code: str | None,
    ibama: IbamaLookup,
    cemaden: CemadenLookup,
) -> DimensionScore:
    indicators: list[RiskIndicator] = []
    points = 0.0
    partial = lat is None or lng is None

    if lat is not None and lng is not None:
        try:
            layers = ibama.contains_point(lat, lng)
            for layer in layers:
                penalty = _LAYER_PENALTY.get(layer, 20)
                points += penalty
                indicators.append(
                    RiskIndicator(
                        code=f"B_{layer}",
                        value=True,
                        source="IBAMA/ICMBio via PostGIS",
                        date_fetched=date.today(),
                        note=f"imóvel dentro de {layer}",
                    )
                )

            risk_zones = cemaden.risk_zones(lat, lng)
            for zone in risk_zones:
                points += 25
                indicators.append(
                    RiskIndicator(
                        code=f"B_CEMADEN_{zone}",
                        value=True,
                        source="CEMADEN via PostGIS",
                        date_fetched=date.today(),
                        note=f"zona de risco: {zone}",
                    )
                )
        except Exception:
            partial = True

    return DimensionScore(
        code="B",
        name="fundiario",
        raw_points=min(points, 100),
        indicators=indicators,
        partial=partial,
    )
