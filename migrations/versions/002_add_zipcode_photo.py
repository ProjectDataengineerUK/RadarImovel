"""Adiciona zipcode e photo_url em properties.

Revision ID: 002
Revises: 001
Create Date: 2026-06-05
"""
import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("properties", sa.Column("zipcode", sa.String(9), nullable=True))
    op.add_column("properties", sa.Column("photo_url", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("properties", "photo_url")
    op.drop_column("properties", "zipcode")
