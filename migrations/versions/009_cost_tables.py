"""Tabela de custos de aquisição por UF (ITBI, registro, escritura).

Revision ID: 009
Revises: 008
Create Date: 2026-06-11
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None

_SEED = [
    ("AC", 2.0000, 0.3000, 0.2500),
    ("AL", 2.0000, 0.2500, 0.2000),
    ("AM", 2.0000, 0.3000, 0.2500),
    ("AP", 2.0000, 0.3000, 0.2500),
    ("BA", 2.0000, 0.3500, 0.3000),
    ("CE", 2.0000, 0.3000, 0.2500),
    ("DF", 3.0000, 0.4000, 0.3500),
    ("ES", 2.0000, 0.3000, 0.2500),
    ("GO", 2.0000, 0.3000, 0.2500),
    ("MA", 2.0000, 0.2500, 0.2000),
    ("MG", 3.0000, 0.4000, 0.3500),
    ("MS", 2.0000, 0.3000, 0.2500),
    ("MT", 2.0000, 0.3000, 0.2500),
    ("PA", 2.0000, 0.2500, 0.2000),
    ("PB", 2.0000, 0.2500, 0.2000),
    ("PE", 2.0000, 0.3500, 0.3000),
    ("PI", 2.0000, 0.2500, 0.2000),
    ("PR", 2.0000, 0.3500, 0.3000),
    ("RJ", 3.0000, 0.4000, 0.3500),
    ("RN", 2.0000, 0.3000, 0.2500),
    ("RO", 2.0000, 0.3000, 0.2500),
    ("RR", 2.0000, 0.3000, 0.2500),
    ("RS", 3.0000, 0.4000, 0.3500),
    ("SC", 2.0000, 0.3500, 0.3000),
    ("SE", 2.0000, 0.2500, 0.2000),
    ("SP", 3.0000, 0.4000, 0.3500),
    ("TO", 2.0000, 0.3000, 0.2500),
]


def upgrade() -> None:
    cost_tables = op.create_table(
        "cost_tables",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("state", sa.String(2), nullable=False, index=True),
        sa.Column("itbi_pct", sa.Numeric(6, 4), nullable=False),
        sa.Column("registro_pct", sa.Numeric(6, 4), nullable=False),
        sa.Column("escritura_pct", sa.Numeric(6, 4), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", UUID(as_uuid=True)),
    )

    op.bulk_insert(
        cost_tables,
        [
            {
                "state": state,
                "itbi_pct": itbi,
                "registro_pct": reg,
                "escritura_pct": esc,
            }
            for state, itbi, reg, esc in _SEED
        ],
    )


def downgrade() -> None:
    op.drop_table("cost_tables")
