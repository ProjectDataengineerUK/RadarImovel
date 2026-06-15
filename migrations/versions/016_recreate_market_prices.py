"""Migration 016: cria market_prices IF NOT EXISTS (recovery).

Alembic pode ter marcado 014/015 sem criar a tabela. Esta migração
cria de forma idempotente para garantir consistência.

Revision ID: 016
Revises: 015
Create Date: 2026-06-15
"""
from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS market_prices (
            id               SERIAL PRIMARY KEY,
            city             VARCHAR(100) NOT NULL,
            uf               VARCHAR(2) NOT NULL,
            property_type    VARCHAR(50),
            price_per_sqm_sale NUMERIC(12, 2),
            price_per_sqm_rent NUMERIC(12, 2),
            price_per_sqm    NUMERIC(12, 2),
            reference_month  DATE NOT NULL,
            source           VARCHAR(50) NOT NULL DEFAULT 'fipezap',
            created_at       TIMESTAMP DEFAULT now(),
            CONSTRAINT uq_market_prices UNIQUE (city, uf, property_type, reference_month, source)
        )
    """)


def downgrade() -> None:
    pass
