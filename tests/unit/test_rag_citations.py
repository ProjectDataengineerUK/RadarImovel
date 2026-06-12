"""Unit tests for AT-009: RAG citation validation."""
import pytest

from app.rag.chat import (
    _build_chunk_map,
    _validate_citations,
    _format_answer,
)


CHUNK_TEXTS = {
    "chunk-1": "O arrematante é responsável pelo pagamento das dívidas de IPTU.",
    "chunk-2": "O imóvel é vendido no estado em que se encontra, sem garantia de ocupação.",
    "chunk-3": "Débitos de condomínio serão pagos pelo arrematante conforme art. 908 do CPC.",
}


class TestBuildChunkMap:
    def test_returns_dict_of_chunk_id_to_text(self):
        from unittest.mock import MagicMock

        chunks = []
        for cid, text in CHUNK_TEXTS.items():
            c = MagicMock()
            c.vector_id = cid
            c.text = text
            chunks.append(c)

        result = _build_chunk_map(chunks)
        assert result == CHUNK_TEXTS

    def test_empty_input(self):
        assert _build_chunk_map([]) == {}


class TestValidateCitations:
    def test_valid_citation_passes(self):
        citations = [
            {"chunk_id": "chunk-1", "quote": "responsável pelo pagamento das dívidas de IPTU"}
        ]
        valid = _validate_citations(citations, CHUNK_TEXTS)
        assert len(valid) == 1
        assert valid[0]["chunk_id"] == "chunk-1"

    def test_quote_not_in_chunk_is_dropped(self):
        citations = [
            {"chunk_id": "chunk-1", "quote": "esta frase não existe no chunk"}
        ]
        valid = _validate_citations(citations, CHUNK_TEXTS)
        assert len(valid) == 0

    def test_unknown_chunk_id_is_dropped(self):
        citations = [
            {"chunk_id": "chunk-999", "quote": "qualquer coisa"}
        ]
        valid = _validate_citations(citations, CHUNK_TEXTS)
        assert len(valid) == 0

    def test_mixed_citations(self):
        citations = [
            {"chunk_id": "chunk-1", "quote": "responsável pelo pagamento das dívidas de IPTU"},
            {"chunk_id": "chunk-2", "quote": "frase inventada"},
            {"chunk_id": "chunk-3", "quote": "Débitos de condomínio serão pagos pelo arrematante"},
        ]
        valid = _validate_citations(citations, CHUNK_TEXTS)
        assert len(valid) == 2
        chunk_ids = [v["chunk_id"] for v in valid]
        assert "chunk-1" in chunk_ids
        assert "chunk-3" in chunk_ids
        assert "chunk-2" not in chunk_ids

    def test_empty_citations_returns_empty(self):
        valid = _validate_citations([], CHUNK_TEXTS)
        assert valid == []

    def test_exact_substring_match_required(self):
        # Case-sensitive: lowercase quote should not match uppercase chunk
        citations = [
            {"chunk_id": "chunk-1", "quote": "iptu"}  # lowercase, chunk has "IPTU"
        ]
        valid = _validate_citations(citations, CHUNK_TEXTS)
        assert len(valid) == 0

    def test_full_chunk_text_as_quote_passes(self):
        citations = [
            {"chunk_id": "chunk-2", "quote": CHUNK_TEXTS["chunk-2"]}
        ]
        valid = _validate_citations(citations, CHUNK_TEXTS)
        assert len(valid) == 1


class TestFormatAnswer:
    def test_valid_answer_with_citations(self):
        raw = {
            "answer": "O arrematante paga o IPTU.",
            "citations": [
                {"chunk_id": "chunk-1", "quote": "responsável pelo pagamento das dívidas de IPTU"}
            ],
            "not_found": False,
        }
        result = _format_answer(raw, CHUNK_TEXTS)
        assert result["not_found"] is False
        assert result["answer"] == "O arrematante paga o IPTU."
        assert len(result["citations"]) == 1

    def test_hallucinated_citation_removed_triggers_not_found(self):
        raw = {
            "answer": "Resposta com citação falsa.",
            "citations": [
                {"chunk_id": "chunk-1", "quote": "citação que não existe no chunk"}
            ],
            "not_found": False,
        }
        result = _format_answer(raw, CHUNK_TEXTS)
        assert result["not_found"] is True
        assert result["citations"] == []

    def test_not_found_flag_respected(self):
        raw = {
            "answer": "",
            "citations": [],
            "not_found": True,
        }
        result = _format_answer(raw, CHUNK_TEXTS)
        assert result["not_found"] is True

    def test_no_citations_with_answer_stays_valid(self):
        raw = {
            "answer": "Esta informação não está explícita, mas infere-se que...",
            "citations": [],
            "not_found": False,
        }
        result = _format_answer(raw, CHUNK_TEXTS)
        assert result["not_found"] is False
        assert result["citations"] == []
