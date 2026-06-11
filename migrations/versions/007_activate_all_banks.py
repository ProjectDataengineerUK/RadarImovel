"""Ativa todos os bancos para coleta (Fase 3 — connectors validados).

Revision ID: 007
Revises: 006
Create Date: 2026-06-11
"""
import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None

BANKS = ["caixa", "bb", "brb", "bnb", "basa", "banrisul", "banestes"]


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE banks SET active = true WHERE code = ANY(:codes)"),
        {"codes": BANKS},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE banks SET active = false WHERE code != 'caixa'"))
