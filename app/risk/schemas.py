from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class RiskLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


class RiskIndicator(BaseModel):
    code: str
    value: Any
    source: str
    date_fetched: date
    note: str | None = None


class DimensionScore(BaseModel):
    code: str  # "A" .. "F"
    name: str
    raw_points: float  # 0-100 before weighting
    indicators: list[RiskIndicator]
    partial: bool = False


class RiskScoreResult(BaseModel):
    score_total: float
    risk_level: str
    score_juridico: float
    score_fundiario: float
    score_fiscal: float
    score_ocupacao: float
    score_socioeconomico: float
    score_mercado: float
    score_partial: bool
    indicators: dict[str, RiskIndicator]
    sources_consulted: list[str]
    calculation_version: str = "1.0"
