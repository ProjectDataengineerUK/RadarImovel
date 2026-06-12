"""POST /properties/{id}/ask — Pergunte ao edital (RAG) — AT-009."""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.middleware.auth import consume_quota, get_current_user, require_feature
from app.core.database import get_db
from app.models.prediction import RagChunk
from app.models.property import Property
from app.models.user import User
from app.rag.chat import AskResponse, ask

router = APIRouter(prefix="/properties", tags=["ask"])


class AskRequest(BaseModel):
    question: str


class CitationOut(BaseModel):
    chunk_id: str
    quote: str


class AskOut(BaseModel):
    answer: str
    citations: list[CitationOut]
    not_found: bool


@router.post("/{id}/ask", response_model=AskOut)
def ask_edital(
    id: uuid.UUID,
    body: AskRequest,
    db: Session = Depends(get_db),
    _feat: User = Depends(require_feature("ask")),
    _quota: User = Depends(consume_quota("ask_per_day")),
    current_user: User = Depends(get_current_user),
) -> Any:
    prop = db.query(Property).filter_by(id=id).first()
    if prop is None:
        raise HTTPException(404, "Imóvel não encontrado")

    has_chunks = db.query(RagChunk).filter_by(property_id=id).first() is not None
    if not has_chunks:
        return AskOut(
            answer="",
            citations=[],
            not_found=True,
        )

    result: AskResponse = ask(db, id, body.question)
    return AskOut(
        answer=result.answer,
        citations=[CitationOut(chunk_id=c.chunk_id, quote=c.quote) for c in result.citations],
        not_found=result.not_found,
    )
