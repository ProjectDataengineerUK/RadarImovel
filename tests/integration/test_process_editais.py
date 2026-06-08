import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import jobs.process_editais as job
from app.models.bank import Bank
from app.models.base import Base
from app.models.document import Document
from app.models.property import Property

FIXTURES = Path(__file__).parents[1] / "fixtures" / "editais"


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
    s.query(Document).delete()
    s.query(Property).delete()
    s.query(Bank).delete()
    s.commit()
    s.close()


@pytest.fixture
def seed(session):
    bank = Bank(id=uuid.uuid4(), code="caixa", name="Caixa Econômica Federal")
    session.add(bank)
    prop = Property(
        id=uuid.uuid4(),
        bank_id=bank.id,
        external_code="EXT1",
        property_type="Apartamento",
        city="Goiânia",
        state="GO",
        appraisal_value=Decimal("200000"),
        minimum_value=Decimal("120000"),
        current_value=Decimal("120000"),
        discount_percent=Decimal("40"),
        occupancy_status="Desocupado",
        sale_modality="Licitação Aberta",
        official_url="https://example.com/1",
        edital_url="https://caixa.gov.br/edital.pdf",
        opportunity_score=80,
        status="active",
        content_hash="h" * 64,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    session.add(prop)
    session.flush()
    return {"bank": bank, "prop": prop}


def _patches(json_fixture="extraction_livre.json"):
    payload = (FIXTURES / json_fixture).read_text()
    return (
        patch.object(job, "download_pdf", return_value=b"%PDF-1.4 fake"),
        patch.object(job, "upload_pdf", return_value="gs://radar-imovel-docs/editais/caixa/GO/x.pdf"),
        patch.object(job, "publish_event"),
        patch(
            "app.connectors.caixa.edital_extractor._generate",
            new=lambda *a, **k: payload,
        ),
        patch("app.connectors.caixa.edital_extractor._init_vertex", new=lambda: None),
    )


def test_happy_path(session, seed):
    p_dl, p_up, p_pub, p_gen, p_init = _patches()
    with p_dl, p_up, p_pub as mock_pub, p_gen, p_init:
        status = job.process_message(
            session,
            {"property_id": str(seed["prop"].id), "edital_url": seed["prop"].edital_url},
        )

    assert status == "done"
    doc = session.query(Document).filter_by(property_id=seed["prop"].id).first()
    assert doc.processing_status == "done"
    summary = json.loads(doc.ai_summary)
    assert sum(1 for v in summary.values() if v not in (None, [], "")) >= 8
    prop = session.query(Property).filter_by(id=seed["prop"].id).first()
    assert prop.risk_level == "low"
    mock_pub.assert_called_once()


def test_idempotencia(session, seed):
    doc = Document(
        property_id=seed["prop"].id,
        bank_id=seed["bank"].id,
        document_type="edital",
        gcs_path="gs://x",
        processing_status="done",
        ai_summary=(FIXTURES / "extraction_livre.json").read_text(),
    )
    session.add(doc)
    session.flush()
    score_before = seed["prop"].opportunity_score

    p_dl, p_up, p_pub, p_gen, p_init = _patches()
    with p_dl, p_up, p_pub as mock_pub, p_gen, p_init:
        status = job.process_message(
            session, {"property_id": str(seed["prop"].id), "edital_url": seed["prop"].edital_url}
        )

    assert status == "done_idempotent"
    assert session.query(Document).filter_by(property_id=seed["prop"].id).count() == 1
    assert seed["prop"].opportunity_score == score_before
    mock_pub.assert_not_called()


def test_url_404(session, seed):
    with patch.object(job, "download_pdf", side_effect=RuntimeError("404 after 3 attempts")), \
         patch.object(job, "publish_event") as mock_pub:
        status = job.process_message(
            session, {"property_id": str(seed["prop"].id), "edital_url": seed["prop"].edital_url}
        )

    assert status == "skipped"
    doc = session.query(Document).filter_by(property_id=seed["prop"].id).first()
    assert doc.processing_status == "skipped"
    assert doc.processing_error
    mock_pub.assert_not_called()


def test_publica_evento_apos_done(session, seed):
    p_dl, p_up, p_pub, p_gen, p_init = _patches()
    with p_dl, p_up, p_pub as mock_pub, p_gen, p_init:
        job.process_message(
            session, {"property_id": str(seed["prop"].id), "edital_url": seed["prop"].edital_url}
        )
    assert mock_pub.call_count == 1
    args = mock_pub.call_args[0]
    assert args[1]["event_type"] == "edital_processed"


def test_property_inexistente_ignora(session):
    with patch.object(job, "publish_event") as mock_pub:
        status = job.process_message(
            session, {"property_id": str(uuid.uuid4()), "edital_url": "https://x"}
        )
    assert status == "ignored"
    mock_pub.assert_not_called()


def test_low_confidence_sem_fallback(session, seed):
    p_dl, p_up, p_pub, p_gen, p_init = _patches("extraction_ocupado.json")
    settings = job.settings
    with p_dl, p_up, p_pub, p_gen, p_init, \
         patch.object(settings, "gemini_fallback_model", ""):
        status = job.process_message(
            session, {"property_id": str(seed["prop"].id), "edital_url": seed["prop"].edital_url}
        )
    assert status == "done"
    doc = session.query(Document).filter_by(property_id=seed["prop"].id).first()
    assert doc.processing_status == "done"
    prop = session.query(Property).filter_by(id=seed["prop"].id).first()
    assert prop.risk_level == "high"
