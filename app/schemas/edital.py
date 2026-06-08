"""Pydantic schemas de saída da API para o bloco `edital`.

Separa o contrato público da API (este arquivo) do schema de extração do LLM
(`app/connectors/caixa/edital_extractor.py`). Todos os campos são opcionais para
suportar graceful degradation quando o edital ainda não foi processado.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class EncumbranceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str
    amount_approx: Decimal | None = None
    description: str = ""


class EditalOut(BaseModel):
    """Bloco `edital` exposto em GET /properties/{id} quando processado."""

    model_config = ConfigDict(from_attributes=True)

    edital_number: str | None = None
    auction_date_1st: date | None = None
    auction_date_2nd: date | None = None
    minimum_bid_1st: Decimal | None = None
    minimum_bid_2nd: Decimal | None = None
    appraisal_value: Decimal | None = None
    payment_modalities: list[str] = []
    occupancy_detail: str | None = None
    encumbrances: list[EncumbranceOut] = []
    total_debt_estimate: Decimal | None = None
    registration_number: str | None = None
    auctioneer_name: str | None = None
    risk_flags: list[str] = []
    risk_level: str | None = None
    extraction_confidence: float | None = None
    processing_status: str | None = None
    processed_at: datetime | None = None
