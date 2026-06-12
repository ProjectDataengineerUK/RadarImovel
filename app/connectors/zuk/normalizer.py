from decimal import Decimal

from app.connectors.base import RawProperty
from app.connectors.normalize_utils import (
    clean_text,
    compute_discount,
    extract_type,
    parse_br_date,
    parse_decimal_br,
    parse_occupancy,
)
from app.core.logging import logger


class ZukNormalizer:
    SOURCE_CODE = "zuk"

    def normalize(self, raw: RawProperty) -> dict:
        d = raw.raw_data
        try:
            current_value = parse_decimal_br(d.get("current_value"))
            appraisal_value = parse_decimal_br(d.get("appraisal_value"))
            discount = compute_discount(appraisal_value, current_value)

            title = clean_text(d.get("title"))
            prop_type = clean_text(d.get("property_type")) or extract_type(title)

            address = clean_text(d.get("address"))
            city = clean_text(d.get("city")) or ""
            state = (clean_text(d.get("state")) or "SP").upper()[:2]

            # Parse area
            area_raw = d.get("area_total")
            area = parse_decimal_br(area_raw) if area_raw else None

            # Parse bedrooms
            try:
                bedrooms = int(d.get("bedrooms") or 0) or None
            except (ValueError, TypeError):
                bedrooms = None

            return {
                "external_code": str(d.get("external_code", raw.external_code)).strip(),
                "bank_code": self.SOURCE_CODE,
                "title": title,
                "property_type": prop_type or "Imóvel",
                "address": address,
                "city": city,
                "state": state,
                "area_total": area,
                "bedrooms": bedrooms,
                "appraisal_value": appraisal_value,
                "minimum_value": current_value or Decimal("0"),
                "current_value": current_value or Decimal("0"),
                "discount_percent": discount,
                "occupancy_status": parse_occupancy(d.get("occupancy_status")),
                "sale_modality": clean_text(d.get("sale_modality")) or "Leilão",
                "auction_date": parse_br_date(d.get("auction_date")),
                "official_url": str(d.get("official_url", "")).strip(),
                "photo_url": clean_text(d.get("photo_url")),
                "status": "active",
            }
        except Exception as exc:
            logger.error("zuk.normalizer.failed", external_code=raw.external_code, error=str(exc))
            raise
