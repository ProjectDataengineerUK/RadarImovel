"""Schema Pydantic público da matrícula — exposto via API."""
from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel, Field


class OnusOut(BaseModel):
    type: str
    credor: str | None = None
    valor_approx: Decimal | None = None
    averbacao: str | None = None


class ProprietarioOut(BaseModel):
    nome: str
    fracao_pct: float | None = None


class MatriculaOut(BaseModel):
    numero_matricula: str | None = None
    cartorio: str | None = None
    area_total_m2: Decimal | None = None
    area_construida_m2: Decimal | None = None
    descricao_resumida: str | None = None
    proprietarios: list[ProprietarioOut] = Field(default_factory=list)
    onus_reais: list[OnusOut] = Field(default_factory=list)
    situacao_dominial: str | None = None
    data_ultima_averbacao: str | None = None
    extraction_confidence: float | None = None
    model_used: str | None = None
    processed_at: str | None = None
