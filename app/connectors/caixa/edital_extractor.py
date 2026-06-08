"""Cliente Vertex AI Gemini para extração estruturada de editais da Caixa.

Define o schema `EditaisExtraction` (espelho do Data Contract da Fase 2),
o prompt de sistema/usuário e `extract_from_gcs(uri)` que chama o Gemini 2.0
Flash com `response_schema` e valida a saída com Pydantic.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.config import get_settings
from app.core.logging import logger

SYSTEM_PROMPT = """\
Você é um analista jurídico-imobiliário especializado em editais de leilão e venda
direta da Caixa Econômica Federal. Sua tarefa é extrair informações estruturadas de
um edital em PDF para alimentar um score de oportunidade de investimento.

REGRAS:
1. Extraia SOMENTE informações explícitas no documento. NUNCA invente valores.
2. Se um campo não constar no edital, retorne null (ou lista vazia para campos de lista).
   Campo ausente é esperado e não é erro — não force um valor aproximado.
3. Valores monetários: número decimal em reais, sem "R$", sem separador de milhar
   (ex: 50000.00). Datas: formato ISO YYYY-MM-DD.
4. occupancy_detail: classifique a situação real de ocupação descrita no edital.
   Use "unknown" apenas se o edital for omisso.
5. encumbrances: liste cada ônus/dívida herdável pelo arrematante (IPTU, condomínio,
   hipoteca). NÃO inclua o lance mínimo nem custas de leilão.
6. total_debt_estimate: some apenas dívidas que o ARREMATANTE assume. Se o edital
   declarar que débitos são quitados com o produto da arrematação, retorne 0.
7. risk_level: classifique low/medium/high considerando ocupação, dívidas vs.
   avaliação e ônus registrados.
8. risk_flags: marque "ocupado" se não-livre, "divida_elevada" se dívidas > 20% da
   avaliação, "onus_registrado" se houver hipoteca/penhora, "area_irregular" se houver
   menção a divergência de área/averbação pendente, "leilao_judicial" se judicial.
9. extraction_confidence: 0.0–1.0 refletindo quão legível/completo era o documento.
   PDF escaneado de baixa qualidade ou texto truncado → confiança baixa.

Responda EXCLUSIVAMENTE com o JSON no schema fornecido. Sem comentários, sem markdown.
"""


class OccupancyDetail(StrEnum):
    livre = "livre"
    ocupado_com_acao_judicial = "ocupado_com_acao_judicial"
    ocupado_sem_acao = "ocupado_sem_acao"
    locado = "locado"
    unknown = "unknown"


class RiskLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class EncumbranceType(StrEnum):
    iptu = "iptu"
    condominio = "condominio"
    hipoteca = "hipoteca"
    outros = "outros"


def _parse_decimal(v: Any) -> Any:
    if v is None or v == "":
        return None
    if isinstance(v, str):
        cleaned = v.replace("R$", "").replace(" ", "")
        if "," in cleaned:
            # Formato BR: ponto é separador de milhar, vírgula é decimal
            cleaned = cleaned.replace(".", "").replace(",", ".")
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
    return v


class Encumbrance(BaseModel):
    type: EncumbranceType
    amount_approx: Decimal | None = None
    description: str = ""

    @field_validator("amount_approx", mode="before")
    @classmethod
    def parse_amount(cls, v: Any) -> Any:
        return _parse_decimal(v)


class EditaisExtraction(BaseModel):
    """Saída estruturada do Gemini 2.0 Flash para um edital da Caixa.

    Espelha o Data Contract do DEFINE (13 campos de negócio + 2 de meta).
    Campos opcionais usam `None` para tolerar editais incompletos.
    """

    edital_number: str | None = None
    auction_date_1st: date | None = None
    auction_date_2nd: date | None = None
    minimum_bid_1st: Decimal | None = None
    minimum_bid_2nd: Decimal | None = None
    appraisal_value: Decimal | None = None
    payment_modalities: list[str] = Field(default_factory=list)
    occupancy_detail: OccupancyDetail = OccupancyDetail.unknown
    encumbrances: list[Encumbrance] = Field(default_factory=list)
    total_debt_estimate: Decimal | None = None
    registration_number: str | None = None
    auctioneer_name: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.medium
    extraction_confidence: float = Field(0.0, ge=0.0, le=1.0)

    @field_validator("occupancy_detail", mode="before")
    @classmethod
    def coerce_occupancy(cls, v: Any) -> Any:
        if v is None or v == "":
            return OccupancyDetail.unknown
        if isinstance(v, str) and v not in OccupancyDetail._value2member_map_:
            return OccupancyDetail.unknown
        return v

    @field_validator("risk_level", mode="before")
    @classmethod
    def coerce_risk(cls, v: Any) -> Any:
        if v is None or v == "":
            return RiskLevel.medium
        if isinstance(v, str) and v not in RiskLevel._value2member_map_:
            return RiskLevel.medium
        return v

    @field_validator(
        "minimum_bid_1st",
        "minimum_bid_2nd",
        "appraisal_value",
        "total_debt_estimate",
        mode="before",
    )
    @classmethod
    def parse_decimal(cls, v: Any) -> Any:
        return _parse_decimal(v)

    @model_validator(mode="after")
    def derive_total_debt(self) -> EditaisExtraction:
        """Se o Gemini não somou, deriva da lista de encumbrances."""
        if self.total_debt_estimate is None:
            known = [e.amount_approx for e in self.encumbrances if e.amount_approx is not None]
            if known:
                self.total_debt_estimate = sum(known, Decimal(0))
        return self


def build_user_prompt(
    property_external_code: str,
    city: str,
    state: str,
    sale_modality: str,
    appraisal_hint: Decimal | float | None,
) -> str:
    hint = f"{appraisal_hint:.2f}" if appraisal_hint is not None else "não informada"
    return (
        f"Extraia os campos do edital anexo (imóvel {property_external_code}, "
        f"{city}/{state}).\n"
        f"Tipo de venda informado na coleta: {sale_modality}.\n"
        f"Avaliação informada na planilha (referência, pode divergir): R$ {hint}."
    )


def _generate(model_name: str, gcs_uri: str, user_prompt: str) -> str:
    from vertexai.generative_models import (
        GenerationConfig,
        GenerativeModel,
        Part,
    )

    model = GenerativeModel(model_name, system_instruction=SYSTEM_PROMPT)
    response = model.generate_content(
        [Part.from_uri(gcs_uri, mime_type="application/pdf"), user_prompt],
        generation_config=GenerationConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=EditaisExtraction.model_json_schema(),
        ),
    )
    return response.text


def _init_vertex() -> None:
    import vertexai

    settings = get_settings()
    project = settings.pubsub_project_id or None
    vertexai.init(project=project, location=settings.vertex_location)


def extract_from_gcs(
    gcs_uri: str,
    *,
    property_external_code: str,
    city: str,
    state: str,
    sale_modality: str,
    appraisal_hint: Decimal | float | None = None,
) -> tuple[EditaisExtraction, str]:
    """Extrai os campos do edital a partir do PDF no GCS.

    Retorna `(extraction, model_used)`. Aplica fallback para o modelo Pro
    apenas se `extraction_confidence < gemini_confidence_floor` e o fallback
    estiver habilitado por config.
    """
    settings = get_settings()
    _init_vertex()
    user_prompt = build_user_prompt(
        property_external_code, city, state, sale_modality, appraisal_hint
    )

    model_used = settings.gemini_model
    raw = _generate(model_used, gcs_uri, user_prompt)
    extraction = EditaisExtraction.model_validate_json(raw)

    if (
        settings.gemini_fallback_model
        and extraction.extraction_confidence < settings.gemini_confidence_floor
    ):
        logger.info(
            "edital_extractor.fallback",
            gcs_uri=gcs_uri,
            confidence=extraction.extraction_confidence,
            fallback_model=settings.gemini_fallback_model,
        )
        model_used = settings.gemini_fallback_model
        raw = _generate(model_used, gcs_uri, user_prompt)
        extraction = EditaisExtraction.model_validate_json(raw)

    logger.info(
        "edital_extractor.extracted",
        gcs_uri=gcs_uri,
        model_used=model_used,
        confidence=extraction.extraction_confidence,
    )
    return extraction, model_used
