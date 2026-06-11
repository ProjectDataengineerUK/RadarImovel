"""Orquestra as 6 dimensões e computa o score final de risco (0-100)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.risk.dimensions import (
    score_fiscal,
    score_fundiario,
    score_juridico,
    score_mercado,
    score_ocupacao,
    score_socioeconomico,
)
from app.risk.schemas import RiskScoreResult
from app.risk.sources.cemaden import CemadenLookup
from app.risk.sources.cnj import CnjClient
from app.risk.sources.fipe import FipeClient
from app.risk.sources.ibama import IbamaLookup
from app.risk.sources.ibge import IbgeLookup
from app.risk.sources.ipea import IpeaAtlas
from app.risk.sources.receita import ReceitaClient
from app.risk.sources.transparencia import TransparenciaClient

_WEIGHTS = {"A": 0.30, "B": 0.20, "C": 0.20, "D": 0.15, "E": 0.10, "F": 0.05}


def calculate_risk(prop, session: Session, settings=None) -> RiskScoreResult:
    if not settings:
        from app.core.config import get_settings
        settings = get_settings()

    extraction = _load_edital_extraction(session, prop.id)

    cnj = CnjClient(timeout=settings.risk_cnj_timeout_s)
    geo_ibama = IbamaLookup(session)
    geo_cemaden = CemadenLookup(session)
    transparencia = TransparenciaClient(timeout=settings.risk_transparencia_timeout_s)
    ibge = IbgeLookup(session)
    ipea = IpeaAtlas()
    receita = ReceitaClient(timeout=settings.risk_ibge_timeout_s)
    fipe = FipeClient(timeout=settings.risk_fipe_timeout_s)

    cnpj_owner = _extract_cnpj(extraction)
    ai_summary = extraction.ai_summary if extraction else None

    dims = [
        score_juridico(
            cnpj_owner=cnpj_owner,
            address=prop.address or "",
            city=prop.city,
            state=prop.state,
            cnj_client=cnj,
        ),
        score_fundiario(
            lat=float(prop.latitude) if prop.latitude else None,
            lng=float(prop.longitude) if prop.longitude else None,
            ibge_code=getattr(prop, "ibge_code", None),
            ibama=geo_ibama,
            cemaden=geo_cemaden,
        ),
        score_fiscal(
            address=prop.address or "",
            city=prop.city,
            state=prop.state,
            appraisal_value=prop.appraisal_value,
            zipcode=prop.zipcode,
            transparencia=transparencia,
            settings=settings,
        ),
        score_ocupacao(
            occupancy_status=prop.occupancy_status,
            address=prop.address or "",
            city=prop.city,
            state=prop.state,
            cnpj_at_address=None,
            ai_summary=ai_summary,
            receita=receita,
            settings=settings,
        ),
        score_socioeconomico(
            ibge_code=getattr(prop, "ibge_code", None),
            ibge=ibge,
            ipea=ipea,
            settings=settings,
        ),
        score_mercado(
            city=prop.city,
            state=prop.state,
            current_value=prop.current_value,
            area_total=prop.area_total,
            fipe=fipe,
        ),
    ]

    total = sum(d.raw_points * _WEIGHTS[d.code] for d in dims)
    total = round(min(max(total, 0.0), 100.0), 1)

    all_indicators = {ind.code: ind for d in dims for ind in d.indicators}
    sources = list(dict.fromkeys(ind.source for d in dims for ind in d.indicators))

    return RiskScoreResult(
        score_total=total,
        risk_level=_classify(total),
        score_juridico=dims[0].raw_points,
        score_fundiario=dims[1].raw_points,
        score_fiscal=dims[2].raw_points,
        score_ocupacao=dims[3].raw_points,
        score_socioeconomico=dims[4].raw_points,
        score_mercado=dims[5].raw_points,
        score_partial=any(d.partial for d in dims),
        indicators=all_indicators,
        sources_consulted=sources,
    )


def _classify(score: float) -> str:
    if score <= 20:
        return "low"
    if score <= 40:
        return "moderate"
    if score <= 60:
        return "elevated"
    if score <= 80:
        return "high"
    return "critical"


def _load_edital_extraction(session: Session, property_id):
    try:
        from app.models.document import Document
        return (
            session.query(Document)
            .filter_by(property_id=property_id, processing_status="done")
            .order_by(Document.processed_at.desc())
            .first()
        )
    except Exception:
        return None


def _extract_cnpj(extraction) -> str | None:
    if not extraction:
        return None
    summary = extraction.ai_summary or {}
    return summary.get("cnpj_owner") or None
