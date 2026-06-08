from decimal import Decimal

from app.connectors.base import RawProperty
from app.connectors.normalize_utils import (
    clean_text,
    compute_discount,
    extract_type,
    parse_decimal_br,
    parse_discount_br,
    parse_occupancy,
)
from app.core.logging import logger


class BBNormalizer:
    BANK_CODE = "bb"

    def normalize(self, raw: RawProperty) -> dict:
        d = raw.raw_data
        try:
            current_value = parse_decimal_br(d.get("current_value"))
            appraisal_value = parse_decimal_br(d.get("appraisal_value"))
            discount_percent = parse_discount_br(d.get("discount_percent"))
            if discount_percent is None:
                discount_percent = compute_discount(appraisal_value, current_value)

            title = clean_text(d.get("title"))
            state = (clean_text(d.get("state")) or "").upper()[:2]

            return {
                "external_code": str(d.get("external_code", "")).strip(),
                "bank_code": self.BANK_CODE,
                "title": title,
                "property_type": extract_type(title),
                "address": clean_text(d.get("address")),
                "neighborhood": clean_text(d.get("neighborhood")),
                "city": clean_text(d.get("city")) or "",
                "state": state,
                "appraisal_value": appraisal_value,
                "minimum_value": current_value or Decimal("0"),
                "current_value": current_value or Decimal("0"),
                "discount_percent": discount_percent,
                "occupancy_status": parse_occupancy(d.get("occupancy_status")),
                "sale_modality": clean_text(d.get("sale_modality")) or "Venda direta",
                "official_url": str(d.get("official_url", "")).strip(),
                "status": "active",
            }
        except Exception as exc:
            logger.error("bb.normalizer.failed", external_code=raw.external_code, error=str(exc))
            raise
