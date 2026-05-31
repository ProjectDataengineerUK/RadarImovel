import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, new_uuid, utcnow


class Document(Base):
    """Documentos brutos associados a imóveis (editais, laudos, etc.).
    Schema completo desde o MVP — Document AI entra na Fase 2 sem migration."""
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    property_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id"))
    bank_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("banks.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)  # edital, laudo, foto
    gcs_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_url: Mapped[str | None] = mapped_column(Text)
    file_size_bytes: Mapped[int | None] = mapped_column()
    mime_type: Mapped[str | None] = mapped_column(String(100))
    extracted_text: Mapped[str | None] = mapped_column(Text)  # Document AI output — Fase 2
    ai_summary: Mapped[str | None] = mapped_column(Text)      # Gemini summary — Fase 2
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
