import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, new_uuid, utcnow


class PricePrediction(Base):
    """Previsão de queda de preço por imóvel e horizonte temporal."""
    __tablename__ = "price_predictions"
    __table_args__ = (
        UniqueConstraint("property_id", "horizon", name="uq_price_predictions_prop_horizon"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)  # 30 | 60 | 90
    probability: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    expected_drop_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    basis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class RagChunk(Base):
    """Trecho de edital/matrícula indexado no Vertex AI Vector Search."""
    __tablename__ = "rag_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_rag_chunks_doc_idx"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    vector_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)


class RadarIndex(Base):
    """Índice mensal de deságio médio por estado/banco — dado público."""
    __tablename__ = "radar_index"
    __table_args__ = (
        UniqueConstraint(
            "period", "state", "bank_code", "property_type",
            name="uq_radar_index",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    period: Mapped[str] = mapped_column(String(7), nullable=False)       # "2026-06"
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    bank_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    property_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    median_discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    p25_discount_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    p75_discount_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
