"""Score de oportunidade.

`calculate_score` (2 sinais) é o cálculo básico da Fase 1 e permanece como
fallback. `calculate_enriched_score` (8+ sinais) usa os campos extraídos do
edital pela Fase 2 e mistura com o básico ponderado pela confiança.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.core.config import get_settings


def calculate_score(property_data: dict) -> int:
    settings = get_settings()
    discount = min(
        float(property_data.get("discount_percent") or 0),
        settings.score_discount_max_points,
    )
    occupancy_bonus = (
        settings.score_occupancy_bonus
        if property_data.get("occupancy_status") == "Desocupado"
        else 0
    )
    return int(min(discount + occupancy_bonus, 100))


_OCCUPANCY_POINTS = {
    "livre": 20,
    "locado": 10,
    "ocupado_sem_acao": 5,
    "ocupado_com_acao_judicial": 0,
    "unknown": 8,
}


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _appraisal(property_data: dict, extraction: dict) -> float | None:
    return (
        _to_float(extraction.get("appraisal_value"))
        or _to_float(property_data.get("appraisal_value"))
    )


def _debt_ratio(property_data: dict, extraction: dict) -> float:
    appraisal = _appraisal(property_data, extraction)
    debt = _to_float(extraction.get("total_debt_estimate")) or 0.0
    if not appraisal or appraisal <= 0:
        return 0.0
    return debt / appraisal


def _discount_score(property_data: dict, extraction: dict) -> float:
    settings = get_settings()
    appraisal = _appraisal(property_data, extraction)
    minimum = (
        _to_float(extraction.get("minimum_bid_1st"))
        or _to_float(property_data.get("minimum_value"))
        or _to_float(property_data.get("current_value"))
    )
    if not appraisal or appraisal <= 0 or minimum is None:
        nominal = _to_float(property_data.get("discount_percent")) or 0.0
        raw = nominal / 100.0
    else:
        raw = (appraisal - minimum) / appraisal
    effective = raw - _debt_ratio(property_data, extraction)
    return max(0.0, min(1.0, effective)) * settings.score_discount_enriched_max


def _occupancy_score(extraction: dict) -> float:
    settings = get_settings()
    detail = extraction.get("occupancy_detail") or "unknown"
    pts = _OCCUPANCY_POINTS.get(detail, 8)
    return min(pts, settings.score_occupancy_enriched_max)


def _payment_score(extraction: dict) -> float:
    settings = get_settings()
    modalities = extraction.get("payment_modalities") or []
    pts = 0
    for m in modalities:
        if m == "financiamento_caixa":
            pts += 4
        elif m == "fgts":
            pts += 4
        elif m == "vista":
            pts += 2
    return min(pts, settings.score_payment_max)


def _auction_proximity(extraction: dict) -> float:
    settings = get_settings()
    raw = extraction.get("auction_date_1st")
    if not raw:
        return 0.0
    if isinstance(raw, date):
        target = raw
    else:
        try:
            target = date.fromisoformat(str(raw))
        except ValueError:
            return 0.0
    days = (target - datetime.now().date()).days
    if 15 <= days <= 60:
        return float(settings.score_proximity_max)
    if 0 <= days < 15 or 60 < days <= 90:
        return settings.score_proximity_max / 2.0
    return 0.0


def _debt_penalty(property_data: dict, extraction: dict) -> float:
    settings = get_settings()
    ratio = _debt_ratio(property_data, extraction)
    return -min(ratio, 1.0) * settings.score_debt_penalty_max


def _risk_flag_penalty(extraction: dict) -> float:
    settings = get_settings()
    flags = extraction.get("risk_flags") or []
    penalty = len(flags) * settings.score_risk_flag_penalty
    return -min(penalty, settings.score_risk_flag_penalty_max)


def _onus_penalty(extraction: dict) -> float:
    settings = get_settings()
    flags = extraction.get("risk_flags") or []
    encs = extraction.get("encumbrances") or []
    has_onus = "onus_registrado" in flags or any(
        (e.get("type") if isinstance(e, dict) else getattr(e, "type", None)) == "hipoteca"
        for e in encs
    )
    return -float(settings.score_onus_penalty) if has_onus else 0.0


def _basic_risk(property_data: dict) -> str:
    return "low" if property_data.get("occupancy_status") == "Desocupado" else "medium"


def _risk_level(property_data: dict, extraction: dict) -> str:
    ratio = _debt_ratio(property_data, extraction)
    flags = extraction.get("risk_flags") or []
    detail = extraction.get("occupancy_detail") or "unknown"
    has_onus = "onus_registrado" in flags
    if ratio > 0.20 or has_onus or detail == "ocupado_com_acao_judicial":
        return "high"
    if detail == "livre" and ratio < 0.05 and not flags:
        return "low"
    gemini = extraction.get("risk_level")
    if gemini in {"low", "medium", "high"}:
        return gemini
    return "medium"


def calculate_enriched_score(
    property_data: dict, extraction: dict | None
) -> tuple[int, str]:
    """Retorna (score 0-100, risk_level). Sem extração → score básico."""
    base = calculate_score(property_data)
    if not extraction:
        return base, _basic_risk(property_data)

    raw = (
        _discount_score(property_data, extraction)
        + _occupancy_score(extraction)
        + _payment_score(extraction)
        + _auction_proximity(extraction)
        + _debt_penalty(property_data, extraction)
        + _risk_flag_penalty(extraction)
        + _onus_penalty(extraction)
    )
    enriched = max(0, min(100, round(raw)))

    conf = _to_float(extraction.get("extraction_confidence")) or 0.0
    conf = max(0.0, min(1.0, conf))
    final = round(conf * enriched + (1 - conf) * base)

    return int(max(0, min(100, final))), _risk_level(property_data, extraction)
