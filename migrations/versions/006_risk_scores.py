"""Risk scores — tabelas property_risk_scores, risk_geodata_layers, ibge_municipality_stats.

Revision ID: 006
Revises: 005
Create Date: 2026-06-10
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "property_risk_scores",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("properties.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("score_total", sa.Numeric(5, 1), nullable=False),
        sa.Column("score_juridico", sa.Numeric(5, 1), nullable=False),
        sa.Column("score_fundiario", sa.Numeric(5, 1), nullable=False),
        sa.Column("score_fiscal", sa.Numeric(5, 1), nullable=False),
        sa.Column("score_ocupacao", sa.Numeric(5, 1), nullable=False),
        sa.Column("score_socioeconomico", sa.Numeric(5, 1), nullable=False),
        sa.Column("score_mercado", sa.Numeric(5, 1), nullable=False),
        sa.Column("risk_level", sa.String(10), nullable=False),
        sa.Column("indicators", pg.JSON, nullable=False, server_default="{}"),
        sa.Column("score_partial", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "sources_consulted",
            pg.ARRAY(sa.Text),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("calculation_version", sa.String(10), nullable=False, server_default="1.0"),
        sa.Column(
            "calculated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_risk_scores_risk_level", "property_risk_scores", ["risk_level"])
    op.create_index("ix_risk_scores_score_total", "property_risk_scores", ["score_total"])

    op.create_table(
        "risk_geodata_layers",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("layer_type", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("attributes", pg.JSON, nullable=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column(
            "loaded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        "SELECT AddGeometryColumn('risk_geodata_layers', 'geom', 4326, 'GEOMETRY', 2)"
    )
    op.create_index("ix_risk_geodata_layer_type", "risk_geodata_layers", ["layer_type"])
    op.execute(
        "CREATE INDEX ix_risk_geodata_geom ON risk_geodata_layers USING GIST (geom)"
    )

    op.create_table(
        "ibge_municipality_stats",
        sa.Column("ibge_code", sa.String(7), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("idh", sa.Numeric(4, 3), nullable=True),
        sa.Column("homicide_rate", sa.Numeric(6, 2), nullable=True),
        sa.Column("population_2022", sa.Integer, nullable=True),
        sa.Column("population_2010", sa.Integer, nullable=True),
        sa.Column("avg_household_income", sa.Numeric(10, 2), nullable=True),
        sa.Column("vacancy_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("ibge_municipality_stats")
    op.execute("DROP INDEX IF EXISTS ix_risk_geodata_geom")
    op.drop_index("ix_risk_geodata_layer_type", "risk_geodata_layers")
    op.drop_table("risk_geodata_layers")
    op.drop_index("ix_risk_scores_score_total", "property_risk_scores")
    op.drop_index("ix_risk_scores_risk_level", "property_risk_scores")
    op.drop_table("property_risk_scores")
