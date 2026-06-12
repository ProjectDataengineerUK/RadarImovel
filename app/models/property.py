import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Text, Numeric, SmallInteger, Date, ForeignKey, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, new_uuid, utcnow


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        Index("ix_properties_state_city", "state", "city"),
        Index("ix_properties_content_hash", "content_hash", unique=True),
        Index("ix_properties_external_code_bank", "external_code", "bank_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    bank_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("banks.id"), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sources.id"))
    external_code: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    property_type: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    neighborhood: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    zipcode: Mapped[str | None] = mapped_column(String(9))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    area_total: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    area_private: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    bedrooms: Mapped[int | None] = mapped_column(SmallInteger)
    parking_spaces: Mapped[int | None] = mapped_column(SmallInteger)
    appraisal_value: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    minimum_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    current_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    discount_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    occupancy_status: Mapped[str] = mapped_column(String(30), nullable=False)
    sale_modality: Mapped[str] = mapped_column(String(50), nullable=False)
    edital_number: Mapped[str | None] = mapped_column(String(50))
    auction_date: Mapped[date | None] = mapped_column(Date)
    auctioneer_name: Mapped[str | None] = mapped_column(String(100))
    auctioneer_url: Mapped[str | None] = mapped_column(Text)
    official_url: Mapped[str] = mapped_column(Text, nullable=False)
    photo_url: Mapped[str | None] = mapped_column(Text)
    edital_url: Mapped[str | None] = mapped_column(Text)
    risk_level: Mapped[str | None] = mapped_column(String(20))
    opportunity_score: Mapped[int | None] = mapped_column(SmallInteger)
    # Onda 3: preço melhor de entre todas as ofertas; None até primeira oferta criada
    best_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # Onda 3: dedup probabilístico — aponta para possível duplicata
    possible_duplicate_of: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    first_seen_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    bank: Mapped["Bank"] = relationship("Bank", back_populates="properties")
    changes: Mapped[list["PropertyChange"]] = relationship("PropertyChange", back_populates="property")
    offers: Mapped[list["PropertyOffer"]] = relationship("PropertyOffer", back_populates="property")


class PropertyOffer(Base):
    """Uma oferta de um imóvel numa fonte específica (banco, leiloeiro, tribunal)."""
    __tablename__ = "property_offers"
    __table_args__ = (
        Index("ix_property_offers_property_source", "property_id", "source_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("banks.id"), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    modality: Mapped[str] = mapped_column(String(50), nullable=False)
    auction_date: Mapped[date | None] = mapped_column(Date)
    official_url: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    external_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    property: Mapped["Property"] = relationship("Property", back_populates="offers")
    source: Mapped["Bank"] = relationship("Bank", back_populates="offers")


class PropertyChange(Base):
    __tablename__ = "property_changes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    property: Mapped["Property"] = relationship("Property", back_populates="changes")
