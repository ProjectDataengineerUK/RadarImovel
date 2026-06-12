"""Migration 012: price_predictions, rag_chunks, radar_index (Onda 4 — Céu Azul)."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "price_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("horizon", sa.Integer, nullable=False),
        sa.Column("probability", sa.Numeric(5, 4), nullable=False),
        sa.Column("expected_drop_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("model_version", sa.String(20), nullable=False),
        sa.Column("basis", postgresql.JSONB, nullable=True),
        sa.Column(
            "computed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("property_id", "horizon", name="uq_price_predictions_prop_horizon"),
    )
    op.create_index("ix_price_predictions_property", "price_predictions", ["property_id"])

    op.create_table(
        "rag_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("vector_id", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_rag_chunks_doc_idx"),
    )
    op.create_index("ix_rag_chunks_property", "rag_chunks", ["property_id"])

    op.create_table(
        "radar_index",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("bank_code", sa.String(20), nullable=True),
        sa.Column("property_type", sa.String(50), nullable=True),
        sa.Column("sample_size", sa.Integer, nullable=False),
        sa.Column("avg_discount_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("median_discount_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("p25_discount_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("p75_discount_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "computed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "period", "state", "bank_code", "property_type", name="uq_radar_index"
        ),
    )
    op.create_index("ix_radar_index_period_state", "radar_index", ["period", "state"])


def downgrade() -> None:
    op.drop_index("ix_radar_index_period_state")
    op.drop_table("radar_index")
    op.drop_index("ix_rag_chunks_property")
    op.drop_table("rag_chunks")
    op.drop_index("ix_price_predictions_property")
    op.drop_table("price_predictions")
