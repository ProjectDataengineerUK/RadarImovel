import json
from decimal import Decimal
from pathlib import Path

from app.connectors.caixa.edital_extractor import (
    EditaisExtraction,
    OccupancyDetail,
    build_user_prompt,
)

FIXTURES = Path(__file__).parents[2] / "fixtures" / "editais"


def test_schema_valida_json_completo():
    raw = (FIXTURES / "extraction_livre.json").read_text()
    extraction = EditaisExtraction.model_validate_json(raw)
    assert extraction.edital_number == "0001234-2026"
    assert extraction.occupancy_detail == OccupancyDetail.livre
    assert "fgts" in extraction.payment_modalities
    assert extraction.extraction_confidence == 0.9


def test_campo_ausente_vira_none():
    data = json.loads((FIXTURES / "extraction_livre.json").read_text())
    data.pop("auctioneer_name")
    extraction = EditaisExtraction.model_validate(data)
    assert extraction.auctioneer_name is None


def test_total_debt_derivado():
    data = {
        "occupancy_detail": "ocupado_sem_acao",
        "encumbrances": [
            {"type": "iptu", "amount_approx": "30000.00"},
            {"type": "condominio", "amount_approx": "20000.00"},
        ],
        "extraction_confidence": 0.8,
    }
    extraction = EditaisExtraction.model_validate(data)
    assert extraction.total_debt_estimate == Decimal("50000.00")


def test_occupancy_enum_invalido_fallback():
    data = {"occupancy_detail": "valor_inexistente", "extraction_confidence": 0.5}
    extraction = EditaisExtraction.model_validate(data)
    assert extraction.occupancy_detail == OccupancyDetail.unknown


def test_risk_level_invalido_fallback():
    data = {"risk_level": "altissimo", "extraction_confidence": 0.5}
    extraction = EditaisExtraction.model_validate(data)
    assert extraction.risk_level.value == "medium"


def test_decimal_de_string():
    data = {"appraisal_value": "200000.50", "extraction_confidence": 0.7}
    extraction = EditaisExtraction.model_validate(data)
    assert extraction.appraisal_value == Decimal("200000.50")


def test_build_user_prompt_inclui_dados():
    prompt = build_user_prompt("1234567", "Goiânia", "GO", "Leilão SFI", Decimal("200000"))
    assert "1234567" in prompt
    assert "Goiânia/GO" in prompt
    assert "Leilão SFI" in prompt


def test_response_schema_serializavel():
    schema = EditaisExtraction.model_json_schema()
    assert "properties" in schema
    assert "occupancy_detail" in schema["properties"]
