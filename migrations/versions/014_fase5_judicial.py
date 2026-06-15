"""Fase 5: judicial + mercado.

Revision ID: 014
Revises: 013
Create Date: 2026-06-14
"""
import sqlalchemy as sa
from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CREATE TABLE IF NOT EXISTS — idempotente (tabela pode já existir por
    # comandos ad-hoc anteriores à migration formal)
    op.execute("""
        CREATE TABLE IF NOT EXISTS market_prices (
            id                 SERIAL PRIMARY KEY,
            city               VARCHAR(100) NOT NULL,
            uf                 VARCHAR(2)   NOT NULL,
            property_type      VARCHAR(50),
            price_per_sqm_sale NUMERIC(12, 2),
            price_per_sqm_rent NUMERIC(12, 2),
            reference_month    DATE         NOT NULL,
            source             VARCHAR(50)  NOT NULL DEFAULT 'fipezap',
            created_at         TIMESTAMP    DEFAULT now(),
            CONSTRAINT uq_market_prices UNIQUE (city, uf, property_type, reference_month, source)
        )
    """)

    # ADD COLUMN IF NOT EXISTS — idempotente
    for col_ddl in [
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS source_type         VARCHAR(20) DEFAULT 'bank'",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS auction_stage        VARCHAR(30)",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS auctioneer_name      VARCHAR(100)",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS process_number       VARCHAR(50)",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS market_price_per_sqm NUMERIC(12,2)",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS discount_vs_market_pct NUMERIC(5,2)",
    ]:
        op.execute(col_ddl)

    op.execute("CREATE INDEX IF NOT EXISTS ix_properties_auction_stage ON properties (auction_stage)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_properties_source_type   ON properties (source_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_properties_process_number ON properties (process_number)")

    op.execute("""
        INSERT INTO banks (code, name, active, source_type, tos_compliant) VALUES
            ('judicial_trt',  'Judicial — TRT',  true, 'court', true),
            ('judicial_trf',  'Judicial — TRF',  true, 'court', true),
            ('judicial_tjsp', 'Judicial — TJSP', true, 'court', true),
            ('lance_certo',   'Lance Certo',     true, 'auctioneer', false),
            ('superleiloes',  'Superleilões',    true, 'auctioneer', false)
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_properties_process_number")
    op.execute("DROP INDEX IF EXISTS ix_properties_source_type")
    op.execute("DROP INDEX IF EXISTS ix_properties_auction_stage")
    op.execute("ALTER TABLE properties DROP COLUMN IF EXISTS discount_vs_market_pct")
    op.execute("ALTER TABLE properties DROP COLUMN IF EXISTS market_price_per_sqm")
    op.execute("ALTER TABLE properties DROP COLUMN IF EXISTS process_number")
    op.execute("ALTER TABLE properties DROP COLUMN IF EXISTS auctioneer_name")
    op.execute("ALTER TABLE properties DROP COLUMN IF EXISTS auction_stage")
    op.execute("ALTER TABLE properties DROP COLUMN IF EXISTS source_type")
    op.execute("DROP TABLE IF EXISTS market_prices")
