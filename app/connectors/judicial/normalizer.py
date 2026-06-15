"""Normaliza RawProperty judicial para schema Property."""
from __future__ import annotations

from decimal import Decimal

from app.connectors.base import RawProperty
from app.connectors.normalize_utils import (
    clean_text,
    extract_type,
    parse_br_date,
    parse_decimal_br,
)
from app.core.logging import logger

_DEFAULT_STATE = "BR"


class JudicialNormalizer:
    def normalize(self, raw: RawProperty) -> dict:
        d = raw.raw_data
        try:
            minimum = parse_decimal_br(str(d.get("minimum_value", "") or "")) or Decimal("0")
            title = clean_text(d.get("title")) or f"Hasta Pública — {d.get('tribunal', '')}"
            state = (clean_text(d.get("state")) or _DEFAULT_STATE).upper()[:2]
            return {
                "external_code": str(raw.external_code).strip(),
                "bank_code": raw.bank_code,
                "title": title,
                "property_type": extract_type(title),
                "address": None,
                "city": clean_text(d.get("city")) or "",
                "state": state,
                "minimum_value": minimum,
                "current_value": minimum,
                "appraisal_value": None,
                "discount_percent": None,
                "occupancy_status": "Não informado",
                "sale_modality": "Hasta Pública",
                "auction_date": parse_br_date(str(d.get("auction_date") or "")),
                "auctioneer_name": clean_text(d.get("auctioneer_name")),
                "official_url": str(d.get("official_url", raw.source_url)).strip(),
                "status": "active",
                "source_type": "judicial",
                "process_number": clean_text(d.get("process_number")),
            }
        except Exception as exc:
            logger.error("judicial.normalize_error", external_code=raw.external_code, error=str(exc))
            raise
