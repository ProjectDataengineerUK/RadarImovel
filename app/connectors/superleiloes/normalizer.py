"""Normalizer Super Leilões → schema Property."""
from __future__ import annotations

from decimal import Decimal

from app.connectors.base import RawProperty
from app.connectors.normalize_utils import (
    clean_text,
    compute_discount,
    extract_type,
    parse_br_date,
    parse_decimal_br,
)
from app.core.logging import logger


class SuperleiloesNormalizer:
    SOURCE_CODE = "superleiloes"

    def normalize(self, raw: RawProperty) -> dict:
        d = raw.raw_data
        try:
            cv = parse_decimal_br(d.get("current_value"))
            av = parse_decimal_br(d.get("appraisal_value"))
            title = clean_text(d.get("title"))
            is_judicial = bool(d.get("process_number"))
            return {
                "external_code": str(raw.external_code).strip(),
                "bank_code": self.SOURCE_CODE,
                "title": title,
                "property_type": extract_type(title),
                "address": None,
                "city": clean_text(d.get("city")) or "",
                "state": (clean_text(d.get("state")) or "BR").upper()[:2],
                "minimum_value": cv or Decimal("0"),
                "current_value": cv or Decimal("0"),
                "appraisal_value": av,
                "discount_percent": compute_discount(av, cv),
                "occupancy_status": "Não informado",
                "sale_modality": "Leilão Judicial" if is_judicial else "Leilão",
                "auction_date": parse_br_date(d.get("auction_date")),
                "official_url": str(d.get("official_url", raw.source_url)).strip(),
                "status": "active",
                "source_type": "judicial" if is_judicial else "auctioneer",
                "process_number": clean_text(d.get("process_number")),
            }
        except Exception as exc:
            logger.error(
                "superleiloes.normalize_error", external_code=raw.external_code, error=str(exc)
            )
            raise
