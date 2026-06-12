import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, Text, TIMESTAMP
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, new_uuid, utcnow


class PropertyRiskScore(Base):
    __tablename__ = "property_risk_scores"
    __table_args__ = (
        Index("ix_risk_scores_risk_level", "risk_level"),
        Index("ix_risk_scores_score_total", "score_total"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id"),
        nullable=False,
        unique=True,
    )
    score_total: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    score_juridico: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    score_fundiario: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    score_fiscal: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    score_ocupacao: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    score_socioeconomico: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    score_mercado: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    indicators: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    score_partial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sources_consulted: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    calculation_version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    calculated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=utcnow, nullable=False
    )

    property: Mapped["Property"] = relationship("Property")  # type: ignore[name-defined]  # noqa: F821


class RiskGeodataLayer(Base):
    __tablename__ = "risk_geodata_layers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    layer_type: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str | None] = mapped_column(String(200))
    # geom column managed by PostGIS/migration, not declared here to avoid geoalchemy2 dep
    attributes: Mapped[dict | None] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


class IbgeMunicipalityStats(Base):
    __tablename__ = "ibge_municipality_stats"

    ibge_code: Mapped[str] = mapped_column(String(7), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    idh: Mapped[float | None] = mapped_column(Numeric(4, 3))
    homicide_rate: Mapped[float | None] = mapped_column(Numeric(6, 2))
    population_2022: Mapped[int | None]
    population_2010: Mapped[int | None]
    avg_household_income: Mapped[float | None] = mapped_column(Numeric(10, 2))
    vacancy_rate: Mapped[float | None] = mapped_column(Numeric(5, 2))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
