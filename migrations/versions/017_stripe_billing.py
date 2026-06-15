"""Stripe billing — stripe_customer_id/subscription_id em users; stripe_price_id/discount_brl em plans.

Revision ID: 017
Revises: 016
Create Date: 2026-06-15
"""
import sqlalchemy as sa
from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users — campos Stripe
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(100)))
    op.add_column("users", sa.Column("stripe_subscription_id", sa.String(100)))
    op.create_index("ix_users_stripe_customer_id", "users", ["stripe_customer_id"], unique=True)

    # plans — stripe price + desconto anual
    op.add_column("plans", sa.Column("stripe_price_id_monthly", sa.String(100)))
    op.add_column("plans", sa.Column("stripe_price_id_annual", sa.String(100)))
    op.add_column("plans", sa.Column("discount_brl", sa.Integer, nullable=False, server_default="0"))
    op.add_column("plans", sa.Column("description", sa.String(255)))
    op.add_column("plans", sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("users", "stripe_customer_id")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("plans", "stripe_price_id_monthly")
    op.drop_column("plans", "stripe_price_id_annual")
    op.drop_column("plans", "discount_brl")
    op.drop_column("plans", "description")
    op.drop_column("plans", "sort_order")
