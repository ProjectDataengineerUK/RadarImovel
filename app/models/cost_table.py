import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, new_uuid, utcnow


class CostTable(Base):
    __tablename__ = "cost_tables"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    state: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    itbi_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    registro_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    escritura_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
