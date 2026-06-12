"""Tabela portfolio_items + coluna extraction_confidence em documents.

Revision ID: 010
Revises: 009
Create Date: 2026-06-11
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("property_id", UUID(as_uuid=True), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("stage", sa.String(30), nullable=False, server_default="monitorando"),
        sa.Column("actual_purchase_price", sa.Numeric(15, 2)),
        sa.Column("actual_renovation_cost", sa.Numeric(15, 2)),
        sa.Column("actual_other_costs", sa.Numeric(15, 2)),
        sa.Column("notes", sa.Text),
        sa.Column("custom_data", sa.JSON, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Adiciona coluna extraction_confidence em documents se ainda não existir
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(sa.Column("extraction_confidence", sa.Numeric(4, 2), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_column("extraction_confidence")
    op.drop_table("portfolio_items")
