"""Integration tests for AT-009: /properties/{id}/ask endpoint."""
import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.main import app
from app.core.database import get_db
from app.models.base import Base


FAKE_UID = "test-ask-uid"
FAKE_EMAIL = "ask@test.com"
AUTH_HEADER = {"Authorization": "Bearer fake-token"}


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
def db(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with patch("app.api.middleware.auth.firebase_auth") as mock_auth:
        mock_auth.verify_id_token.return_value = {"uid": FAKE_UID, "email": FAKE_EMAIL}
        yield TestClient(app)
    app.dependency_overrides.clear()


def _make_ask_response(answer="", citations=None, not_found=False):
    from app.rag.chat import AskResponse, Citation
    return AskResponse(
        answer=answer,
        citations=[Citation(**c) for c in (citations or [])],
        not_found=not_found,
    )


class TestAskEndpointAuth:
    def test_requires_auth(self, client: TestClient):
        resp = client.post(f"/properties/{uuid.uuid4()}/ask", json={"question": "test"})
        assert resp.status_code in (401, 403)

    def test_requires_question_field(self, db):
        from fastapi import HTTPException
        from pydantic import ValidationError
        from app.api.routes.ask import AskRequest

        with pytest.raises((ValidationError, Exception)):
            AskRequest(**{})  # missing question field


class TestAskRouteUnit:
    """Tests calling the route function directly, bypassing HTTP stack."""

    def test_property_not_found_raises_404(self, db):
        from fastapi import HTTPException
        from app.api.routes.ask import ask_edital, AskRequest

        body = AskRequest(question="test")

        with patch.object(db, "query") as mock_q:
            mock_q.return_value.filter_by.return_value.first.return_value = None
            with pytest.raises(HTTPException) as exc_info:
                ask_edital(
                    id=uuid.uuid4(),
                    body=body,
                    db=db,
                    _feat=MagicMock(),
                    _quota=MagicMock(),
                    current_user=MagicMock(),
                )
        assert exc_info.value.status_code == 404

    def test_no_chunks_returns_not_found(self, db):
        from app.api.routes.ask import ask_edital, AskRequest

        body = AskRequest(question="test")
        prop = MagicMock()
        prop.id = uuid.uuid4()

        with patch.object(db, "query") as mock_q:
            mock_q.return_value.filter_by.return_value.first.side_effect = [
                prop,
                None,  # no RagChunk
            ]
            result = ask_edital(
                id=prop.id,
                body=body,
                db=db,
                _feat=MagicMock(),
                _quota=MagicMock(),
                current_user=MagicMock(),
            )

        assert result.not_found is True
        assert result.answer == ""
        assert result.citations == []

    def test_valid_answer_with_citations(self, db):
        from app.api.routes.ask import ask_edital, AskRequest
        from app.rag.chat import Citation

        body = AskRequest(question="Quem paga o IPTU?")
        prop = MagicMock()
        prop.id = uuid.uuid4()
        mock_chunk = MagicMock()
        mock_resp = _make_ask_response(
            answer="O arrematante é responsável.",
            citations=[{"chunk_id": "c1", "quote": "O arrematante paga o IPTU."}],
        )

        with patch("app.api.routes.ask.ask", return_value=mock_resp), \
             patch.object(db, "query") as mock_q:
            mock_q.return_value.filter_by.return_value.first.side_effect = [prop, mock_chunk]
            result = ask_edital(
                id=prop.id,
                body=body,
                db=db,
                _feat=MagicMock(),
                _quota=MagicMock(),
                current_user=MagicMock(),
            )

        assert result.not_found is False
        assert len(result.citations) == 1
        assert result.citations[0].quote == "O arrematante paga o IPTU."

    def test_not_found_flag_when_gemini_returns_not_found(self, db):
        from app.api.routes.ask import ask_edital, AskRequest

        body = AskRequest(question="Algo fora do edital")
        prop = MagicMock()
        prop.id = uuid.uuid4()
        mock_chunk = MagicMock()
        mock_resp = _make_ask_response(answer="", citations=[], not_found=True)

        with patch("app.api.routes.ask.ask", return_value=mock_resp), \
             patch.object(db, "query") as mock_q:
            mock_q.return_value.filter_by.return_value.first.side_effect = [prop, mock_chunk]
            result = ask_edital(
                id=prop.id,
                body=body,
                db=db,
                _feat=MagicMock(),
                _quota=MagicMock(),
                current_user=MagicMock(),
            )

        assert result.not_found is True
        assert result.citations == []

    def test_citation_serialization_preserves_fields(self, db):
        from app.api.routes.ask import ask_edital, AskRequest

        body = AskRequest(question="Quem é o responsável?")
        prop = MagicMock()
        prop.id = uuid.uuid4()
        mock_chunk = MagicMock()
        mock_resp = _make_ask_response(
            answer="Resposta aqui.",
            citations=[
                {"chunk_id": "chunk-A", "quote": "trecho do edital"},
                {"chunk_id": "chunk-B", "quote": "outro trecho"},
            ],
        )

        with patch("app.api.routes.ask.ask", return_value=mock_resp), \
             patch.object(db, "query") as mock_q:
            mock_q.return_value.filter_by.return_value.first.side_effect = [prop, mock_chunk]
            result = ask_edital(
                id=prop.id,
                body=body,
                db=db,
                _feat=MagicMock(),
                _quota=MagicMock(),
                current_user=MagicMock(),
            )

        assert len(result.citations) == 2
        quotes = [c.quote for c in result.citations]
        assert "trecho do edital" in quotes
        assert "outro trecho" in quotes
