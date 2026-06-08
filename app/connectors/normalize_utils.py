"""Helpers de parsing de valores brasileiros compartilhados entre connectors.

Extraídos do `caixa/normalizer.py` na Fase 3 para reuso por todos os bancos.
Todos defensivos: nunca levantam exceção, retornam None/default em caso de erro.
"""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def parse_decimal_br(value: str | None) -> Decimal | None:
    """Converte moeda/numero BR ('106.667,03') em Decimal. None se inválido."""
    if value is None:
        return None
    s = re.sub(r"[^\d,.]", "", str(value))
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_discount_br(value: str | None) -> Decimal | None:
    """Converte percentual de desconto ('25,5%' / '25.5' / '2550') em Decimal."""
    if value is None:
        return None
    cleaned = re.sub(r"[^\d,.]", "", str(value)).replace(",", ".")
    if not cleaned:
        return None
    try:
        d = Decimal(cleaned)
    except InvalidOperation:
        return None
    return d if d <= 100 else d / 100


def parse_occupancy(value: str | None) -> str:
    """Normaliza situação de ocupação para 'Ocupado'/'Desocupado'/texto/Não informado."""
    if not value:
        return "Não informado"
    v = str(value).strip().lower()
    if "desocup" in v or "livre" in v or "vazio" in v:
        return "Desocupado"
    if "ocup" in v:
        return "Ocupado"
    return str(value).strip()


def clean_text(value: str | None) -> str | None:
    """Colapsa espaços/quebras e remove bordas; None se vazio."""
    if value is None:
        return None
    s = re.sub(r"\s+", " ", str(value)).strip()
    return s or None


def extract_type(title: str | None) -> str:
    """Extrai o tipo do imóvel do início da descrição ('Casa, 62m²' → 'Casa')."""
    if not title:
        return "Imóvel"
    head = re.split(r"[,\-–|]", str(title), maxsplit=1)[0].strip()
    return head or "Imóvel"


_DATE_FORMATS = ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y")


def parse_br_date(value: str | None) -> date | None:
    """Converte data BR ('08/06/2026') em date. None se inválido."""
    if not value:
        return None
    s = str(value).strip()
    match = re.search(r"\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4}", s)
    if match:
        s = match.group(0)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def compute_discount(
    appraisal_value: Decimal | None, current_value: Decimal | None
) -> Decimal | None:
    """Calcula desconto % a partir de avaliação e preço atual, se possível."""
    if appraisal_value and current_value and appraisal_value > 0:
        return ((appraisal_value - current_value) / appraisal_value * 100).quantize(
            Decimal("0.01")
        )
    return None
