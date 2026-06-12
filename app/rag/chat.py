"""RAG chat: recupera chunks do Vertex AI Vector Search e responde com Gemini.

Regras de citação (AT-009):
- Toda resposta deve conter ao menos 1 citação cujo trecho exista verbatim no chunk.
- Se não houver citações válidas, retorna `not_found=True`.
- Citação alucinada (trecho não presente no chunk) é descartada server-side.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import logger
from app.models.prediction import RagChunk

if TYPE_CHECKING:
    pass

_ASK_SYSTEM_PROMPT = """\
Você é um assistente jurídico-imobiliário que responde perguntas sobre o edital \
e matrícula de um imóvel. Responda SOMENTE com informações presentes nos trechos \
fornecidos. Cite o trecho exato que embasou cada parte da resposta.

REGRAS:
1. Se a informação não constar nos trechos fornecidos, retorne not_found=true e \
answer vazio.
2. Cada citation.quote deve ser copiada literalmente do trecho correspondente.
3. Nunca invente, suponha ou extrapole informações além do que está escrito.
4. Responda em português do Brasil.
"""

_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "answer": {"type": "STRING"},
        "citations": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "chunk_id": {"type": "STRING"},
                    "quote": {"type": "STRING"},
                },
                "required": ["chunk_id", "quote"],
            },
        },
        "not_found": {"type": "BOOLEAN"},
    },
    "required": ["answer", "citations", "not_found"],
}


@dataclass
class Citation:
    chunk_id: str
    quote: str


@dataclass
class AskResponse:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    not_found: bool = False


def _build_chunk_map(chunks: list[RagChunk]) -> dict[str, str]:
    return {c.vector_id: c.text for c in chunks}


def _validate_citations(
    citations: list[dict], chunk_texts: dict[str, str]
) -> list[dict]:
    """Descarta citações cujo quote não existe verbatim no chunk referenciado."""
    valid = []
    for cit in citations:
        cid = cit.get("chunk_id", "")
        quote = cit.get("quote", "").strip()
        text = chunk_texts.get(cid, "")
        if quote and text and quote in text:
            valid.append(cit)
    return valid


def _format_answer(raw: dict, chunk_texts: dict[str, str]) -> dict:
    raw_cits = raw.get("citations") or []
    valid_cits = _validate_citations(raw_cits, chunk_texts)
    all_citations_stripped = bool(raw_cits) and not valid_cits
    not_found = raw.get("not_found", False) or all_citations_stripped or not raw.get("answer", "").strip()
    return {
        "answer": raw.get("answer", ""),
        "citations": valid_cits,
        "not_found": not_found,
    }


def _retrieve_chunks(session: Session, property_id: Any, query: str, k: int) -> list[RagChunk]:
    """Retrieves top-k chunks for the property. Uses Vector Search when available."""
    settings = get_settings()
    try:
        from google.cloud import aiplatform
        import vertexai
        from vertexai.language_models import TextEmbeddingModel

        vertexai.init(location=settings.vertex_location)
        embed_model = TextEmbeddingModel.from_pretrained("text-embedding-005")
        query_emb = embed_model.get_embeddings([query])[0].values

        aiplatform.init(location=settings.vertex_location)
        endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=settings.vertex_index_endpoint_id
        )
        response = endpoint.find_neighbors(
            deployed_index_id=settings.vertex_deployed_index_id,
            queries=[query_emb],
            num_neighbors=k,
            filter=[
                aiplatform.MatchingEngineIndexEndpoint.FindNeighborsRequest.Query.RefinedFilter(
                    namespace="property_id", allow_list=[str(property_id)]
                )
            ],
        )
        vector_ids = [n.id for n in response[0]]
        if not vector_ids:
            return _fallback_chunks(session, property_id, k)
        chunks = (
            session.query(RagChunk)
            .filter(RagChunk.vector_id.in_(vector_ids), RagChunk.property_id == property_id)
            .all()
        )
        return chunks or _fallback_chunks(session, property_id, k)
    except Exception as exc:
        logger.warning("rag.retrieval_fallback", error=str(exc))
        return _fallback_chunks(session, property_id, k)


def _fallback_chunks(session: Session, property_id: Any, k: int) -> list[RagChunk]:
    return (
        session.query(RagChunk)
        .filter(RagChunk.property_id == property_id)
        .order_by(RagChunk.chunk_index)
        .limit(k)
        .all()
    )


def _call_gemini(context: str, question: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        import vertexai
        from vertexai.generative_models import GenerationConfig, GenerativeModel

        vertexai.init(location=settings.vertex_location)
        model = GenerativeModel(settings.gemini_model, system_instruction=_ASK_SYSTEM_PROMPT)
        prompt = f"TRECHOS DO EDITAL:\n{context}\n\nPERGUNTA: {question}"
        resp = model.generate_content(
            prompt,
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                response_schema=_RESPONSE_SCHEMA,
            ),
        )
        return json.loads(resp.text)
    except Exception as exc:
        logger.error("rag.gemini_error", error=str(exc))
        return {"answer": "", "citations": [], "not_found": True}


def ask(session: Session, property_id: Any, question: str, k: int = 6) -> AskResponse:
    chunks = _retrieve_chunks(session, property_id, question, k)
    if not chunks:
        return AskResponse(answer="", not_found=True)

    chunk_map = _build_chunk_map(chunks)
    context = "\n\n".join(
        f"[{cid}]\n{text}" for cid, text in chunk_map.items()
    )
    raw = _call_gemini(context, question)
    formatted = _format_answer(raw, chunk_map)

    return AskResponse(
        answer=formatted["answer"],
        citations=[Citation(c["chunk_id"], c["quote"]) for c in formatted["citations"]],
        not_found=formatted["not_found"],
    )
