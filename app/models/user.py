import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, BigInteger, Boolean, ForeignKey, Numeric, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, new_uuid, utcnow

USER_ROLES = ("user", "suporte", "operador", "admin")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)  # PII — nunca logar, nunca expor
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    notification_channels: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("subscriptions.id"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    watchlists: Mapped[list["Watchlist"]] = relationship("Watchlist", back_populates="user")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="user")
    favorites: Mapped[list["Favorite"]] = relationship("Favorite", back_populates="user")
    subscription: Mapped["Subscription | None"] = relationship(  # type: ignore[name-defined]
        "Subscription", foreign_keys=[subscription_id], lazy="joined"
    )


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    state: Mapped[str | None] = mapped_column(String(2))
    city: Mapped[str | None] = mapped_column(String(100))
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    min_discount: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    property_type: Mapped[str | None] = mapped_column(String(50))
    bank_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("banks.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="watchlists")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    watchlist_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("watchlists.id"))
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="telegram")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="alerts")


class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="favorites")
