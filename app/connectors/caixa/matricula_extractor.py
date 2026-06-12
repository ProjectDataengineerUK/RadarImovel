"""Extrator de matrícula do imóvel via Gemini (mesmo padrão do edital_extractor).

Processa um PDF de matrícula/certidão de inteiro teor do cartório de registro
de imóveis e retorna `MatriculaExtraction` com ônus, proprietários e área.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings
from app.core.logging import logger

SYSTEM_PROMPT = """\
Você é um analista jurídico-imobiliário especializado em matrículas e certidões
de registro de imóveis do Brasil. Sua tarefa é extrair informações estruturadas
de um PDF de matrícula ou certidão de inteiro teor.

REGRAS:
1. Extraia SOMENTE informações explícitas no documento. NUNCA invente valores.
2. Se um campo não constar no documento, retorne null.
3. Área: número decimal em m² (ex: 120.50). Valores monetários: decimal em reais, sem "R$".
4. onus_reais: liste APENAS gravames ativos (hipoteca, penhora, alienação fiduciária,
   usufruto, servidão). NÃO inclua averbações canceladas ou liquidadas.
5. situacao_dominial: classifique com base nos proprietários e transmissões registradas.
6. extraction_confidence: 0.0–1.0 refletindo legibilidade. PDF escaneado → confiança baixa.

Responda EXCLUSIVAMENTE com o JSON no schema fornecido. Sem comentários, sem markdown.
"""


def _parse_decimal(v: Any) -> Any:
    if v is None or v == "":
        return None
    if isinstance(v, str):
        cleaned = v.replace("R$", "").replace(" ", "")
        if "," in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
    return v


class OnusType(StrEnum):
    hipoteca = "hipoteca"
    penhora = "penhora"
    alienacao_fiduciaria = "alienacao_fiduciaria"
    usufruto = "usufruto"
    servidao = "servidao"
    outros = "outros"


class SituacaoDominial(StrEnum):
    plena_propriedade = "plena_propriedade"
    copropriedade = "copropriedade"
    dominio_util = "dominio_util"
    usufruto_vigente = "usufruto_vigente"
    controverso = "controverso"
    unknown = "unknown"


class Onus(BaseModel):
    type: OnusType
    credor: str | None = None
    valor_approx: Decimal | None = None
    averbacao: str | None = None

    @field_validator("valor_approx", mode="before")
    @classmethod
    def parse_valor(cls, v: Any) -> Any:
        return _parse_decimal(v)


class Proprietario(BaseModel):
    nome: str
    cpf_cnpj_parcial: str | None = None
    fracao_pct: float | None = None


class MatriculaExtraction(BaseModel):
    numero_matricula: str | None = None
    cartorio: str | None = None
    area_total_m2: Decimal | None = None
    area_construida_m2: Decimal | None = None
    descricao_resumida: str | None = None
    proprietarios: list[Proprietario] = Field(default_factory=list)
    onus_reais: list[Onus] = Field(default_factory=list)
    situacao_dominial: SituacaoDominial = SituacaoDominial.unknown
    data_ultima_averbacao: str | None = None
    numero_contribuinte_iptu: str | None = None
    extraction_confidence: float = Field(0.0, ge=0.0, le=1.0)

    @field_validator("area_total_m2", "area_construida_m2", mode="before")
    @classmethod
    def parse_area(cls, v: Any) -> Any:
        return _parse_decimal(v)

    @field_validator("situacao_dominial", mode="before")
    @classmethod
    def coerce_situacao(cls, v: Any) -> Any:
        if v is None or v == "":
            return SituacaoDominial.unknown
        if isinstance(v, str) and v not in SituacaoDominial._value2member_map_:
            return SituacaoDominial.unknown
        return v


def _init_vertex() -> None:
    import vertexai
    settings = get_settings()
    vertexai.init(project=settings.pubsub_project_id or None, location=settings.vertex_location)


def _generate(model_name: str, gcs_uri: str, property_code: str) -> str:
    from vertexai.generative_models import GenerationConfig, GenerativeModel, Part

    model = GenerativeModel(model_name, system_instruction=SYSTEM_PROMPT)
    user_prompt = f"Extraia os dados da matrícula do imóvel {property_code} no documento anexo."
    response = model.generate_content(
        [Part.from_uri(gcs_uri, mime_type="application/pdf"), user_prompt],
        generation_config=GenerationConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=MatriculaExtraction.model_json_schema(),
        ),
    )
    return response.text


def extract_matricula_from_gcs(
    gcs_uri: str,
    *,
    property_external_code: str,
) -> tuple[MatriculaExtraction, str]:
    """Extrai dados de matrícula do PDF no GCS. Retorna (extraction, model_used)."""
    settings = get_settings()
    _init_vertex()

    model_used = settings.gemini_model
    raw = _generate(model_used, gcs_uri, property_external_code)
    extraction = MatriculaExtraction.model_validate_json(raw)

    if (
        settings.gemini_fallback_model
        and extraction.extraction_confidence < settings.gemini_confidence_floor
    ):
        logger.info(
            "matricula_extractor.fallback",
            gcs_uri=gcs_uri,
            confidence=extraction.extraction_confidence,
        )
        model_used = settings.gemini_fallback_model
        raw = _generate(model_used, gcs_uri, property_external_code)
        extraction = MatriculaExtraction.model_validate_json(raw)

    logger.info(
        "matricula_extractor.extracted",
        gcs_uri=gcs_uri,
        model=model_used,
        confidence=extraction.extraction_confidence,
        onus_count=len(extraction.onus_reais),
    )
    return extraction, model_used
