import io
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
import openpyxl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.bank import Bank
from app.models.property import Property


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
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(prop)
    db_session.flush()
    return prop


@pytest.fixture
def fake_xlsx_bytes():
    """XLSX com 3 imóveis simulando o formato da Caixa."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([
        "Número do imóvel", "UF", "Cidade", "Bairro", "Endereço",
        "Preço", "Valor de avaliação", "Desconto",
        "Descrição", "Modalidade de venda", "Link de acesso",
        "Situação do imóvel", "Tipo do imóvel",
    ])
    ws.append([
        "7654321", "SP", "São Paulo", "Centro", "Rua da Consolação, 100",
        "350000", "450000", "22.2",
        "Apartamento 2 quartos", "Licitação Aberta",
        "https://venda-imoveis.caixa.gov.br/imovel/7654321",
        "Desocupado", "Apartamento",
    ])
    ws.append([
        "7654322", "SP", "Campinas", "Jardins", "Av. Brasil, 200",
        "180000", "220000", "18.2",
        "Casa 3 quartos", "Venda Direta",
        "https://venda-imoveis.caixa.gov.br/imovel/7654322",
        "Ocupado", "Casa",
    ])
    ws.append([
        "7654323", "SP", "Santos", "Gonzaga", "Rua do Porto, 50",
        "500000", "600000", "16.7",
        "Apartamento frente mar", "Leilão SFI",
        "https://venda-imoveis.caixa.gov.br/imovel/7654323",
        "Desocupado", "Apartamento",
    ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture
def mock_telegram():
    mock = MagicMock()
    mock.send = MagicMock(return_value=True)
    return mock
