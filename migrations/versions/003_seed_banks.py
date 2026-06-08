"""Seed tabela banks com bancos monitorados.

Revision ID: 003
Revises: 002
Create Date: 2026-06-08
"""
import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

BANKS = [
    ("caixa", "Caixa Econômica Federal", True),
    ("bb", "Banco do Brasil", False),
    ("brb", "BRB", False),
    ("bnb", "Banco do Nordeste", False),
    ("basa", "Banco da Amazônia", False),
    ("banrisul", "Banrisul", False),
    ("banestes", "Banestes", False),
]


def upgrade() -> None:
    conn = op.get_bind()
    for code, name, active in BANKS:
        conn.execute(
            sa.text(
                "INSERT INTO banks (code, name, active) "
                "VALUES (:code, :name, :active) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            {"code": code, "name": name, "active": active},
        )


def downgrade() -> None:
    op.get_bind().execute(sa.text("DELETE FROM banks WHERE code IN ('caixa','bb','brb','bnb','basa','banrisul','banestes')"))
