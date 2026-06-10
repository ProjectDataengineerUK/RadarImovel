from decimal import Decimal

from app.connectors.base import RawProperty
from app.connectors.normalize_utils import (
    compute_discount,
    extract_type,
    parse_decimal_br,
    parse_discount_br,
    parse_occupancy,
)
from app.core.logging import logger


def _s(val, default: str | None = None) -> str | None:
    """Converte valor para str, retornando None se for nulo, vazio ou 'nan'."""
    if val is None:
        return default
    s = str(val).strip()
    return default if (not s or s.lower() == "nan") else s


class CaixaNormalizer:
    BANK_CODE = "caixa"

    def normalize(self, raw: RawProperty) -> dict:
        d = raw.raw_data
        try:
            current_value = parse_decimal_br(d.get("current_value"))
            appraisal_value = parse_decimal_br(d.get("appraisal_value"))
            discount_percent = parse_discount_br(d.get("discount_percent"))

            if discount_percent is None:
                discount_percent = compute_discount(appraisal_value, current_value)

            official_url = _s(d.get("official_url"))
            # URL inválida (ex: "nan") vira None para não quebrar o detail scraper
            if official_url and not official_url.startswith("http"):
                official_url = None

            return {
                "external_code": _s(d.get("external_code"), ""),
                "bank_code": self.BANK_CODE,
                "title": _s(d.get("title")),
                "property_type": extract_type(d.get("title")),
                "address": _s(d.get("address")),
                "neighborhood": _s(d.get("neighborhood")),
                "city": _s(d.get("city"), ""),
                "state": _s(d.get("state"), "")[:2].upper(),
                "appraisal_value": appraisal_value,
                "minimum_value": current_value or Decimal("0"),
                "current_value": current_value or Decimal("0"),
                "discount_percent": discount_percent,
                "occupancy_status": parse_occupancy(d.get("occupancy_status")),
                "sale_modality": _s(d.get("sale_modality"), "Não informado"),
                "official_url": official_url,
                "status": "active",
            }
        except Exception as exc:
            logger.error("caixa.normalizer.failed", external_code=raw.external_code, error=str(exc))
            raise
