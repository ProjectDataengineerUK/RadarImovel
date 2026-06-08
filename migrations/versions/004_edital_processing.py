"""Edital processing control columns on documents.

Revision ID: 004
Revises: 003
Create Date: 2026-06-08
"""
import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("processing_status", sa.String(20), nullable=False, server_default="pending"),
    )
    op.add_column("documents", sa.Column("processing_error", sa.Text(), nullable=True))
    op.add_column(
        "documents",
        sa.Column("processed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("extraction_confidence", sa.Numeric(3, 2), nullable=True),
    )

    # Índice parcial: o job só precisa varrer pendentes/falhos (reprocessamento manual)
    op.create_index(
        "ix_documents_pending",
        "documents",
        ["processing_status"],
        postgresql_where=sa.text("processing_status IN ('pending', 'failed')"),
    )

    # Garante unicidade de edital por imóvel (Data Contract: zero duplicação)
    op.create_index(
        "uq_documents_property_edital",
        "documents",
        ["property_id", "document_type"],
        unique=True,
        postgresql_where=sa.text("document_type = 'edital'"),
    )


def downgrade() -> None:
    op.drop_index("uq_documents_property_edital", table_name="documents")
    op.drop_index("ix_documents_pending", table_name="documents")
    op.drop_column("documents", "extraction_confidence")
    op.drop_column("documents", "processed_at")
    op.drop_column("documents", "processing_error")
    op.drop_column("documents", "processing_status")
