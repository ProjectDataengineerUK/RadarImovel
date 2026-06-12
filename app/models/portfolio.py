import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Text, ForeignKey, Numeric, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, new_uuid, utcnow

KANBAN_STAGES = ("monitorando", "analisando", "proposta", "arrematado", "descartado")


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(30), nullable=False, default="monitorando")
    actual_purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    actual_renovation_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    actual_other_costs: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    custom_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    user: Mapped["User"] = relationship("User")  # type: ignore[name-defined]
    property: Mapped["Property"] = relationship("Property")  # type: ignore[name-defined]
