import re
from decimal import Decimal, InvalidOperation
from app.connectors.base import RawProperty
from app.core.logging import logger


def _parse_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    cleaned = re.sub(r"[^\d,.]", "", str(value)).replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _parse_discount(value: str | None) -> Decimal | None:
    if not value:
        return None
    cleaned = re.sub(r"[^\d,.]", "", str(value)).replace(",", ".")
    try:
        d = Decimal(cleaned)
        return d if d <= 100 else d / 100  # normalize % se vier como inteiro
    except InvalidOperation:
        return None


def _normalize_occupancy(value: str | None) -> str:
    if not value:
        return "Não informado"
    v = str(value).strip().lower()
    if "desocup" in v:
        return "Desocupado"
    if "ocup" in v:
        return "Ocupado"
    return str(value).strip()


class CaixaNormalizer:
    BANK_CODE = "caixa"

    def normalize(self, raw: RawProperty) -> dict:
        d = raw.raw_data
        try:
            current_value = _parse_decimal(d.get("current_value"))
            appraisal_value = _parse_decimal(d.get("appraisal_value"))
            discount_percent = _parse_discount(d.get("discount_percent"))

            if discount_percent is None and current_value and appraisal_value and appraisal_value > 0:
                discount_percent = ((appraisal_value - current_value) / appraisal_value * 100).quantize(Decimal("0.01"))

            return {
                "external_code": str(d.get("external_code", "")).strip(),
                "bank_code": self.BANK_CODE,
                "title": str(d.get("title", "")).strip() or None,
                "property_type": str(d.get("property_type", "Imóvel")).strip(),
                "address": str(d.get("address", "")).strip() or None,
                "neighborhood": str(d.get("neighborhood", "")).strip() or None,
                "city": str(d.get("city", "")).strip(),
                "state": str(d.get("state", "")).strip().upper()[:2],
                "appraisal_value": appraisal_value,
                "minimum_value": current_value or Decimal("0"),
                "current_value": current_value or Decimal("0"),
                "discount_percent": discount_percent,
                "occupancy_status": _normalize_occupancy(d.get("occupancy_status")),
                "sale_modality": str(d.get("sale_modality", "Não informado")).strip(),
                "official_url": str(d.get("official_url", "")).strip(),
                "status": "active",
            }
        except Exception as exc:
            logger.error("caixa.normalizer.failed", external_code=raw.external_code, error=str(exc))
            raise
