from datetime import date
from decimal import Decimal

from app.connectors.normalize_utils import (
    clean_text,
    compute_discount,
    extract_type,
    parse_br_date,
    parse_decimal_br,
    parse_discount_br,
    parse_occupancy,
)


def test_parse_decimal_br_milhar_e_decimal():
    assert parse_decimal_br("106.667,03") == Decimal("106667.03")


def test_parse_decimal_br_so_decimal():
    assert parse_decimal_br("1500,50") == Decimal("1500.50")


def test_parse_decimal_br_com_prefixo_moeda():
    assert parse_decimal_br("R$ 240.000,00") == Decimal("240000.00")


def test_parse_decimal_br_none_e_vazio():
    assert parse_decimal_br(None) is None
    assert parse_decimal_br("") is None
    assert parse_decimal_br("abc") is None


def test_parse_discount_br_percentual():
    assert parse_discount_br("25,5%") == Decimal("25.5")


def test_parse_discount_br_normaliza_acima_de_100():
    assert parse_discount_br("2550") == Decimal("25.50")


def test_parse_discount_br_none():
    assert parse_discount_br(None) is None


def test_parse_occupancy_variantes():
    assert parse_occupancy("Imóvel desocupado") == "Desocupado"
    assert parse_occupancy("Ocupado pelo mutuário") == "Ocupado"
    assert parse_occupancy(None) == "Não informado"
    assert parse_occupancy("Livre") == "Desocupado"


def test_clean_text_colapsa_espacos():
    assert clean_text("  Rua   das\n Flores ") == "Rua das Flores"
    assert clean_text(None) is None
    assert clean_text("   ") is None


def test_extract_type():
    assert extract_type("Casa, 62m², 2 quartos") == "Casa"
    assert extract_type("Apartamento - 78m²") == "Apartamento"
    assert extract_type(None) == "Imóvel"


def test_parse_br_date():
    assert parse_br_date("15/07/2026") == date(2026, 7, 15)
    assert parse_br_date("Data: 22/08/2026") == date(2026, 8, 22)
    assert parse_br_date(None) is None
    assert parse_br_date("sem data") is None


def test_compute_discount():
    assert compute_discount(Decimal("200000"), Decimal("150000")) == Decimal("25.00")
    assert compute_discount(None, Decimal("100")) is None
    assert compute_discount(Decimal("0"), Decimal("100")) is None
