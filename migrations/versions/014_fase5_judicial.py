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
    op.create_table(
        "market_prices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("uf", sa.String(2), nullable=False),
        sa.Column("property_type", sa.String(50)),
        sa.Column("price_per_sqm_sale", sa.Numeric(12, 2)),
        sa.Column("price_per_sqm_rent", sa.Numeric(12, 2)),
        sa.Column("reference_month", sa.Date(), nullable=False),
        sa.Column("source", sa.String(50), server_default="fipezap"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "city", "uf", "property_type", "reference_month", "source",
            name="uq_market_prices",
        ),
    )

    op.add_column("properties", sa.Column("source_type", sa.String(20), server_default="bank"))
    op.add_column("properties", sa.Column("auction_stage", sa.String(30)))
    op.add_column("properties", sa.Column("auctioneer_name", sa.String(100)))
    op.add_column("properties", sa.Column("process_number", sa.String(50)))
    op.add_column("properties", sa.Column("market_price_per_sqm", sa.Numeric(12, 2)))
    op.add_column("properties", sa.Column("discount_vs_market_pct", sa.Numeric(5, 2)))

    op.create_index("ix_properties_auction_stage", "properties", ["auction_stage"])
    op.create_index("ix_properties_source_type", "properties", ["source_type"])
    op.create_index("ix_properties_process_number", "properties", ["process_number"])

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
    op.drop_index("ix_properties_process_number")
    op.drop_index("ix_properties_source_type")
    op.drop_index("ix_properties_auction_stage")
    op.drop_column("properties", "discount_vs_market_pct")
    op.drop_column("properties", "market_price_per_sqm")
    op.drop_column("properties", "process_number")
    op.drop_column("properties", "auctioneer_name")
    op.drop_column("properties", "auction_stage")
    op.drop_column("properties", "source_type")
    op.drop_table("market_prices")
