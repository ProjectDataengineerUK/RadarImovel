"""RAG indexer: chunks edital/matrícula e indexa no Vertex AI Vector Search.

Fluxo:
  extracted_text (Document) → chunk_text → embed (text-embedding-005) →
  upsert_vector_search → salva RagChunk no DB com vector_id.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import logger
from app.models.prediction import RagChunk

if TYPE_CHECKING:
    from app.models.document import Document

CHUNK_SIZE = 500   # chars por chunk (≈ 100–130 tokens)
CHUNK_OVERLAP = 80  # sobreposição para não quebrar contexto


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if not text or not text.strip():
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start += size - overlap
    return [c for c in chunks if c]


def _embed_chunks(chunks: list[str], settings) -> list[list[float]]:
    """Chama text-embedding-005 via Vertex AI. Retorna lista de vetores 768-dim."""
    try:
        import vertexai
        from vertexai.language_models import TextEmbeddingModel

        vertexai.init(location=settings.vertex_location)
        model = TextEmbeddingModel.from_pretrained("text-embedding-005")
        embeddings = model.get_embeddings(chunks)
        return [e.values for e in embeddings]
    except Exception as exc:
        logger.warning("rag.embed_error", error=str(exc))
        return [[] for _ in chunks]


def _upsert_vector_search(
    property_id: str, chunk_ids: list[str], embeddings: list[list[float]], settings
) -> None:
    """Faz upsert de datapoints no Vertex AI Vector Search via streaming update."""
    if not embeddings or not embeddings[0]:
        return
    try:
        from google.cloud import aiplatform

        aiplatform.init(location=settings.vertex_location)
        index = aiplatform.MatchingEngineIndex(index_name=settings.vertex_index_id)
        datapoints = [
            aiplatform.MatchingEngineIndex.Datapoint(
                datapoint_id=cid,
                feature_vector=emb,
                restricts=[
                    aiplatform.MatchingEngineIndex.Datapoint.Restriction(
                        namespace="property_id", allow_list=[property_id]
                    )
                ],
            )
            for cid, emb in zip(chunk_ids, embeddings)
            if emb
        ]
        if datapoints:
            index.upsert_datapoints(datapoints=datapoints)
    except Exception as exc:
        logger.warning("rag.vector_search_upsert_error", error=str(exc))


def index_document(session: Session, document: "Document") -> int:
    """Indexa um documento: chunka o texto, embeda e salva no DB + Vector Search.
    Retorna o número de chunks criados/atualizados.
    """
    settings = get_settings()
    text = document.extracted_text or ""
    if not text.strip():
        logger.info("rag.skip_empty_text", document_id=str(document.id))
        return 0

    chunks = chunk_text(text)
    if not chunks:
        return 0

    property_id = str(document.property_id)
    chunk_ids: list[str] = []
    rag_chunks: list[RagChunk] = []

    for idx, chunk in enumerate(chunks):
        existing = (
            session.query(RagChunk)
            .filter_by(document_id=document.id, chunk_index=idx)
            .first()
        )
        cid = str(existing.id) if existing else str(uuid.uuid4())
        chunk_ids.append(cid)

        if existing:
            existing.text = chunk
            rag_chunks.append(existing)
        else:
            rc = RagChunk(
                id=uuid.UUID(cid),
                property_id=document.property_id,
                document_id=document.id,
                chunk_index=idx,
                text=chunk,
            )
            session.add(rc)
            rag_chunks.append(rc)

    session.flush()

    embeddings = _embed_chunks(chunks, settings)
    _upsert_vector_search(property_id, chunk_ids, embeddings, settings)

    for rc, cid in zip(rag_chunks, chunk_ids):
        rc.vector_id = cid

    logger.info(
        "rag.indexed",
        document_id=str(document.id),
        property_id=property_id,
        chunks=len(chunks),
    )
    return len(chunks)
