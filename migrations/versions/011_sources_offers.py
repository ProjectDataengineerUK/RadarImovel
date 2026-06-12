"""Onda 3: banks generalizado para sources (source_type, tos_compliant),
property_offers (1 imóvel N ofertas), best_price em properties,
possible_duplicate_of em properties.

Revision ID: 011
Revises: 010
Create Date: 2026-06-11
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── banks: novos campos para generalização ────────────────────────────────
    op.add_column("banks", sa.Column("source_type", sa.String(20), nullable=False, server_default="bank"))
    op.add_column("banks", sa.Column("tos_compliant", sa.Boolean(), nullable=False, server_default="true"))

    # ── properties: best_price + possible_duplicate_of ────────────────────────
    op.add_column("properties", sa.Column("best_price", sa.Numeric(15, 2), nullable=True))
    op.add_column(
        "properties",
        sa.Column(
            "possible_duplicate_of",
            UUID(as_uuid=True),
            sa.ForeignKey("properties.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_properties_possible_dup", "properties", ["possible_duplicate_of"])

    # ── property_offers ───────────────────────────────────────────────────────
    op.create_table(
        "property_offers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("property_id", UUID(as_uuid=True), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("banks.id"), nullable=False),
        sa.Column("price", sa.Numeric(15, 2), nullable=False),
        sa.Column("modality", sa.String(50), nullable=False),
        sa.Column("auction_date", sa.Date(), nullable=True),
        sa.Column("official_url", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("external_code", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_property_offers_property_source", "property_offers", ["property_id", "source_id"], unique=True)

    # ── backfill best_price = current_value ───────────────────────────────────
    op.execute("UPDATE properties SET best_price = current_value WHERE best_price IS NULL")

    # ── seeds: leiloeiros na tabela banks ────────────────────────────────────
    # tos_compliant=false até validação jurídica individual de cada ToS
    op.execute("""
        INSERT INTO banks (id, code, name, active, source_type, tos_compliant)
        VALUES
          (gen_random_uuid(), 'zuk',     'Portal Zuk',         true, 'auctioneer', false),
          (gen_random_uuid(), 'mega',    'Mega Leilões',        true, 'auctioneer', false),
          (gen_random_uuid(), 'sodre',   'Sodré Santoro',       true, 'auctioneer', false),
          (gen_random_uuid(), 'fidalgo', 'Fidalgo Leilões',     true, 'auctioneer', false),
          (gen_random_uuid(), 'frazao',  'Frazão Leilões',      true, 'auctioneer', false),
          (gen_random_uuid(), 'tjsp',    'TJ-SP Hasta Pública', true, 'court',      true)
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table("property_offers")
    op.drop_index("ix_properties_possible_dup", "properties")
    op.drop_column("properties", "possible_duplicate_of")
    op.drop_column("properties", "best_price")
    op.drop_column("banks", "tos_compliant")
    op.drop_column("banks", "source_type")
