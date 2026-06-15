"""Migration 015: price_per_sqm em market_prices + seed banks judicial/tjsp.

Revision ID: 015
Revises: 014
Create Date: 2026-06-15
"""
from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE market_prices ADD COLUMN IF NOT EXISTS price_per_sqm NUMERIC(12, 2)
    """)
    op.execute("""
        UPDATE market_prices
        SET price_per_sqm = price_per_sqm_sale
        WHERE price_per_sqm_sale IS NOT NULL AND price_per_sqm IS NULL
    """)
    op.execute("""
        INSERT INTO banks (code, name, active, source_type, tos_compliant) VALUES
            ('judicial', 'Judicial — DataJud (TRT/TRF)', true, 'court', true),
            ('tjsp',     'TJSP — Tribunal de Justiça SP', true, 'court', true)
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM banks WHERE code IN ('judicial', 'tjsp')")
    op.execute("ALTER TABLE market_prices DROP COLUMN IF EXISTS price_per_sqm")
