"""Migration 019: adiciona last_scraped_at à tabela banks.

Permite distinguir "job nunca rodou" de "job rodou mas achou 0 imóveis",
corrigindo o dashboard Sentinela que usava MAX(p.last_seen_at) como proxy.

Revision ID: 019
Revises: 018
Create Date: 2026-06-16
"""
from alembic import op

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE banks
        ADD COLUMN IF NOT EXISTS last_scraped_at TIMESTAMP WITH TIME ZONE
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE banks DROP COLUMN IF EXISTS last_scraped_at")
