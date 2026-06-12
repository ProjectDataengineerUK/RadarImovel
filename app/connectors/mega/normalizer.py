from decimal import Decimal

from app.connectors.base import RawProperty
from app.connectors.normalize_utils import (
    clean_text, compute_discount, extract_type,
    parse_br_date, parse_decimal_br, parse_occupancy,
)
from app.core.logging import logger


class MegaNormalizer:
    SOURCE_CODE = "mega"

    def normalize(self, raw: RawProperty) -> dict:
        d = raw.raw_data
        try:
            cv = parse_decimal_br(d.get("current_value"))
            av = parse_decimal_br(d.get("appraisal_value"))
            title = clean_text(d.get("title"))
            return {
                "external_code": str(d.get("external_code", raw.external_code)).strip(),
                "bank_code": self.SOURCE_CODE,
                "title": title,
                "property_type": clean_text(d.get("property_type")) or extract_type(title),
                "address": clean_text(d.get("address")),
                "city": clean_text(d.get("city")) or "",
                "state": (clean_text(d.get("state")) or "SP").upper()[:2],
                "area_total": parse_decimal_br(d.get("area_total")),
                "appraisal_value": av,
                "minimum_value": cv or Decimal("0"),
                "current_value": cv or Decimal("0"),
                "discount_percent": compute_discount(av, cv),
                "occupancy_status": parse_occupancy(d.get("occupancy_status")),
                "sale_modality": clean_text(d.get("sale_modality")) or "Leilão",
                "auction_date": parse_br_date(d.get("auction_date")),
                "official_url": str(d.get("official_url", "")).strip(),
                "photo_url": clean_text(d.get("photo_url")),
                "status": "active",
            }
        except Exception as exc:
            logger.error("mega.normalizer.failed", external_code=raw.external_code, error=str(exc))
            raise
