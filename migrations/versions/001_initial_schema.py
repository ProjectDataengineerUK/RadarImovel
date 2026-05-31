"""Initial schema — todas as tabelas do MVP Fase 1.

Revision ID: 001
Revises:
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "banks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("bank_id", UUID(as_uuid=True), sa.ForeignKey("banks.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "properties",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("bank_id", UUID(as_uuid=True), sa.ForeignKey("banks.id"), nullable=False),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("external_code", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("property_type", sa.String(50), nullable=False),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("neighborhood", sa.String(100), nullable=True),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("area_total", sa.Numeric(10, 2), nullable=True),
        sa.Column("area_private", sa.Numeric(10, 2), nullable=True),
        sa.Column("bedrooms", sa.SmallInteger, nullable=True),
        sa.Column("parking_spaces", sa.SmallInteger, nullable=True),
        sa.Column("appraisal_value", sa.Numeric(15, 2), nullable=True),
        sa.Column("minimum_value", sa.Numeric(15, 2), nullable=False),
        sa.Column("current_value", sa.Numeric(15, 2), nullable=False),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("occupancy_status", sa.String(30), nullable=False),
        sa.Column("sale_modality", sa.String(50), nullable=False),
        sa.Column("edital_number", sa.String(50), nullable=True),
        sa.Column("auction_date", sa.Date, nullable=True),
        sa.Column("auctioneer_name", sa.String(100), nullable=True),
        sa.Column("auctioneer_url", sa.Text, nullable=True),
        sa.Column("official_url", sa.Text, nullable=False),
        sa.Column("edital_url", sa.Text, nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("opportunity_score", sa.SmallInteger, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("first_seen_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.UniqueConstraint("external_code", "bank_id", name="uq_properties_external_bank"),
    )
    op.create_index("ix_properties_state_city", "properties", ["state", "city"])

    op.create_table(
        "property_changes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("property_id", UUID(as_uuid=True), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("field_name", sa.String(50), nullable=False),
        sa.Column("old_value", sa.Text, nullable=True),
        sa.Column("new_value", sa.Text, nullable=True),
        sa.Column("detected_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("firebase_uid", sa.String(128), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "watchlists",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("max_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("min_discount", sa.Numeric(5, 2), nullable=True),
        sa.Column("property_type", sa.String(50), nullable=True),
        sa.Column("bank_id", UUID(as_uuid=True), sa.ForeignKey("banks.id"), nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("property_id", UUID(as_uuid=True), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("watchlist_id", UUID(as_uuid=True), sa.ForeignKey("watchlists.id"), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False, server_default="telegram"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "favorites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("property_id", UUID(as_uuid=True), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("property_id", UUID(as_uuid=True), sa.ForeignKey("properties.id"), nullable=True),
        sa.Column("bank_id", UUID(as_uuid=True), sa.ForeignKey("banks.id"), nullable=False),
        sa.Column("document_type", sa.String(30), nullable=False),
        sa.Column("gcs_path", sa.Text, nullable=False),
        sa.Column("original_url", sa.Text, nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("extracted_text", sa.Text, nullable=True),
        sa.Column("ai_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Seed: banco Caixa
    op.execute(
        "INSERT INTO banks (id, code, name) VALUES (uuid_generate_v4(), 'caixa', 'Caixa Econômica Federal')"
    )


def downgrade() -> None:
    op.drop_table("documents")
    op.drop_table("favorites")
    op.drop_table("alerts")
    op.drop_table("watchlists")
    op.drop_table("users")
    op.drop_table("property_changes")
    op.drop_index("ix_properties_state_city", "properties")
    op.drop_table("properties")
    op.drop_table("sources")
    op.drop_table("banks")
