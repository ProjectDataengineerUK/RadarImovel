import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.bank import Bank
from app.models.base import Base
from app.models.document import Document
from app.models.property import Property

FIXTURES_EDITAIS = Path(__file__).parent / "fixtures" / "editais"


@pytest.fixture(scope="session")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_bank(db_session):
    bank = Bank(id=uuid.uuid4(), code="caixa", name="Caixa Econômica Federal")
    db_session.add(bank)
    db_session.flush()
    return bank


@pytest.fixture
def sample_property(db_session, sample_bank):
    prop = Property(
        id=uuid.uuid4(),
        bank_id=sample_bank.id,
        external_code="1234567",
        property_type="Apartamento",
        city="Goiânia",
        state="GO",
        minimum_value=Decimal("150000.00"),
        current_value=Decimal("200000.00"),
        discount_percent=Decimal("25.00"),
        occupancy_status="Desocupado",
        sale_modality="Licitação Aberta",
        official_url="https://venda-imoveis.caixa.gov.br/imovel/1234567",
        status="active",
        content_hash="abc123def456" + "0" * 52,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    db_session.add(prop)
    db_session.flush()
    return prop


@pytest.fixture
def fake_csv_bytes():
    """CSV no formato atual da Caixa (sep=';', latin-1, 2 linhas antes do header)."""
    content = (
        "\n"
        " Lista de Imóveis da Caixa;;Data de geração:;01/01/2026;;;;;;;\n"
        " N° do imóvel;UF;Cidade;Bairro;Endereço;Preço;Valor de avaliação;Desconto;Financiamento;Descrição;Modalidade de venda;Link de acesso\n"
        "7654321;SP;São Paulo;Centro;Rua da Consolação, 100;350.000,00;450.000,00;22.2;Não;Apartamento, 2 quartos;Licitação Aberta;https://venda-imoveis.caixa.gov.br/imovel/7654321\n"
        "7654322;SP;Campinas;Jardins;Av. Brasil, 200;180.000,00;220.000,00;18.2;Sim;Casa, 3 quartos;Venda Direta;https://venda-imoveis.caixa.gov.br/imovel/7654322\n"
        "7654323;SP;Santos;Gonzaga;Rua do Porto, 50;500.000,00;600.000,00;16.7;Não;Apartamento, frente mar;Leilão SFI;https://venda-imoveis.caixa.gov.br/imovel/7654323\n"
    )
    return content.encode("latin-1")


@pytest.fixture
def mock_telegram():
    mock = MagicMock()
    mock.send = MagicMock(return_value=True)
    return mock


@pytest.fixture
def document_factory(db_session, sample_bank):
    """Cria um Document de edital para um Property dado."""

    def _make(property_id, *, status="pending", ai_summary=None, confidence=None):
        doc = Document(
            id=uuid.uuid4(),
            property_id=property_id,
            bank_id=sample_bank.id,
            document_type="edital",
            gcs_path="gs://radar-imovel-docs/editais/caixa/GO/x.pdf",
            original_url="https://caixa.gov.br/edital.pdf",
            processing_status=status,
            ai_summary=ai_summary,
            extraction_confidence=Decimal(str(confidence)) if confidence is not None else None,
        )
        db_session.add(doc)
        db_session.flush()
        return doc

    return _make


@pytest.fixture
def mock_vertex(monkeypatch):
    """Substitui a geração do Gemini por uma resposta determinística (JSON fixture)."""

    def _make(json_path):
        payload = Path(json_path).read_text()

        def _gen(model_name, gcs_uri, user_prompt):
            return payload

        monkeypatch.setattr(
            "app.connectors.caixa.edital_extractor._generate", _gen
        )
        monkeypatch.setattr(
            "app.connectors.caixa.edital_extractor._init_vertex", lambda: None
        )
        return json.loads(payload)

    return _make


@pytest.fixture
def mock_gcs(monkeypatch):
    """Patch de storage.Client para upload no-op retornando URI fake."""

    uploaded = {}

    class _Blob:
        def __init__(self, name):
            self.name = name

        def upload_from_string(self, data, content_type=None):
            uploaded["data"] = data
            uploaded["content_type"] = content_type

    class _Bucket:
        def __init__(self, name):
            self.name = name

        def blob(self, name):
            uploaded["blob_path"] = name
            return _Blob(name)

    class _Client:
        def bucket(self, name):
            return _Bucket(name)

    monkeypatch.setattr("jobs.process_editais.storage.Client", lambda *a, **k: _Client())
    return uploaded
