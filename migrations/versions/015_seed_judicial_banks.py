"""Migration 015: price_per_sqm em market_prices + seed banks judicial/tjsp.

Revision ID: 015
Revises: 014
Create Date: 2026-06-15
"""
import sqlalchemy as sa
from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Coluna price_per_sqm omitida em 014; o model SQLAlchemy a inclui como alias
    # de price_per_sqm_sale para compatibilidade com código legado
    op.add_column(
        "market_prices",
        sa.Column("price_per_sqm", sa.Numeric(12, 2), nullable=True),
    )

    # Backfill: price_per_sqm = price_per_sqm_sale onde já há dados
    op.execute("""
        UPDATE market_prices
        SET price_per_sqm = price_per_sqm_sale
        WHERE price_per_sqm_sale IS NOT NULL
    """)

    # Seeds: judicial (genérico p/ TRT*/TRF*) e tjsp (chave SOURCE_REGISTRY)
    op.execute("""
        INSERT INTO banks (code, name, active, source_type, tos_compliant) VALUES
            ('judicial', 'Judicial — DataJud (TRT/TRF)', true, 'court', true),
            ('tjsp',     'TJSP — Tribunal de Justiça SP', true, 'court', true)
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM banks WHERE code IN ('judicial', 'tjsp')")
    op.drop_column("market_prices", "price_per_sqm")
