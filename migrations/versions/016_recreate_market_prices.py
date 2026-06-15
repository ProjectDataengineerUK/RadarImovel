"""Migration 016: recovery — aplica 014+015 de forma idempotente.

O banco foi marcado como '015' sem que as migrations 014 e 015 tivessem
sido executadas. Esta migration usa IF NOT EXISTS / DO NOTHING para
aplicar todos os artefatos em falta de forma segura.

Revision ID: 016
Revises: 015
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. market_prices (criada em 014) ───────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS market_prices (
            id                 SERIAL PRIMARY KEY,
            city               VARCHAR(100) NOT NULL,
            uf                 VARCHAR(2)   NOT NULL,
            property_type      VARCHAR(50),
            price_per_sqm_sale NUMERIC(12, 2),
            price_per_sqm_rent NUMERIC(12, 2),
            price_per_sqm      NUMERIC(12, 2),
            reference_month    DATE         NOT NULL,
            source             VARCHAR(50)  NOT NULL DEFAULT 'fipezap',
            created_at         TIMESTAMP    DEFAULT now(),
            CONSTRAINT uq_market_prices UNIQUE (city, uf, property_type, reference_month, source)
        )
    """)

    # ── 2. Colunas em properties (adicionadas em 014) ──────────────────────
    for col_ddl in [
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS source_type        VARCHAR(20)    DEFAULT 'bank'",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS auction_stage       VARCHAR(30)",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS auctioneer_name     VARCHAR(100)",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS process_number      VARCHAR(50)",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS market_price_per_sqm NUMERIC(12,2)",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS discount_vs_market_pct NUMERIC(5,2)",
    ]:
        op.execute(col_ddl)

    # ── 3. Índices (IF NOT EXISTS compatível com PG ≥ 9.5) ────────────────
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_properties_auction_stage
            ON properties (auction_stage)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_properties_source_type
            ON properties (source_type)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_properties_process_number
            ON properties (process_number)
    """)

    # ── 4. Seeds de banks (014 + 015) ─────────────────────────────────────
    op.execute("""
        INSERT INTO banks (code, name, active, source_type, tos_compliant) VALUES
            ('judicial_trt',  'Judicial — TRT',                      true, 'court', true),
            ('judicial_trf',  'Judicial — TRF',                      true, 'court', true),
            ('judicial_tjsp', 'Judicial — TJSP',                     true, 'court', true),
            ('lance_certo',   'Lance Certo',                         true, 'auctioneer', false),
            ('superleiloes',  'Superleilões',                        true, 'auctioneer', false),
            ('judicial',      'Judicial — DataJud (TRT/TRF)',        true, 'court', true),
            ('tjsp',          'TJSP — Tribunal de Justiça SP',       true, 'court', true)
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    pass
