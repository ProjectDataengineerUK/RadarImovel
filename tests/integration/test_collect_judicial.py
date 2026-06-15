"""Integration test: collect_judicial job end-to-end com DataJud mockado."""
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.bank import Bank, Source
from app.models.property import Property

_MOCK_HITS = [
    {
        "process_number": "0001234-56.2024.5.02.0001",
        "tribunal": "TRT2",
        "summary": "Hasta Pública — Apartamento em São Paulo/SP",
        "city": "São Paulo",
        "state": "SP",
        "minimum_value": 350000.0,
        "hasta_date": "2026-07-15",
        "process_url": "https://datajud.cnj.jus.br/processo/0001234-56.2024.5.02.0001",
        "auctioneer": None,
    },
    {
        "process_number": "0009876-11.2024.5.02.0050",
        "tribunal": "TRT2",
        "summary": "Hasta Pública — Casa em Guarulhos/SP",
        "city": "Guarulhos",
        "state": "SP",
        "minimum_value": 180000.0,
        "hasta_date": "2026-07-20",
        "process_url": "https://datajud.cnj.jus.br/processo/0009876-11.2024.5.02.0050",
        "auctioneer": None,
    },
]


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.rollback()
    s.close()


@pytest.fixture
def seeded_bank(session):
    bank = Bank(id=uuid.uuid4(), code="judicial", name="Judicial — TRT", active=True)
    session.add(bank)
    source = Source(
        id=uuid.uuid4(),
        bank_id=bank.id,
        name="DataJud TRT2",
        url="datajud://TRT2",
        source_type="court",
        active=True,
    )
    session.add(source)
    session.commit()
    yield bank
    session.query(Property).delete()
    session.query(Source).delete()
    session.query(Bank).delete()
    session.commit()


def test_judicial_job_inserts_properties(session, seeded_bank):
    """DataJud mockado → connector parseia → propriedades inseridas no DB."""
    from app.connectors.judicial import JudicialConnector

    connector = JudicialConnector(tribunal="TRT2", days_back=30)

    with patch.object(connector._client, "search_hastas_tribunal", return_value=_MOCK_HITS):
        raw = connector.fetch_raw("TRT2:0")
        hits = json.loads(raw)
        assert len(hits) == 2

        props = list(connector.parse(raw, "TRT2:0"))
        assert len(props) == 2
        assert props[0].external_code == "0001234-56.2024.5.02.0001"
        assert props[0].raw_data["city"] == "São Paulo"
        assert props[0].raw_data["minimum_value"] == 350000.0

        normalized = [connector.normalize(p) for p in props]
        for n in normalized:
            assert n["source_type"] == "judicial"
            assert n["state"] == "SP"


def test_judicial_fetch_empty_returns_empty_bytes(session, seeded_bank):
    from app.connectors.judicial import JudicialConnector

    connector = JudicialConnector(tribunal="TRT2", days_back=30)
    with patch.object(connector._client, "search_hastas_tribunal", return_value=[]):
        raw = connector.fetch_raw("TRT2:0")
        assert raw == b""
        props = list(connector.parse(raw, "TRT2:0"))
        assert props == []
