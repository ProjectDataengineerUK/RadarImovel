"""Planos, assinaturas, RBAC, contadores de uso e audit log.

Revision ID: 008
Revises: 007
Create Date: 2026-06-11
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── plans ──────────────────────────────────────────────────────────────────
    op.create_table(
        "plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("price_brl", sa.Integer, nullable=False, server_default="0"),
        sa.Column("features", JSONB, nullable=False, server_default="'{}'"),
        sa.Column("limits", JSONB, nullable=False, server_default="'{}'"),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── subscriptions ──────────────────────────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan_id", UUID(as_uuid=True), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])

    # ── users: add role, notification_channels, subscription_id ───────────────
    op.add_column("users", sa.Column("role", sa.String(20), nullable=False, server_default="user"))
    op.add_column("users", sa.Column("notification_channels", JSONB, nullable=False, server_default="'{}'"))
    op.add_column("users", sa.Column("subscription_id", UUID(as_uuid=True), sa.ForeignKey("subscriptions.id")))

    # ── usage_counters ─────────────────────────────────────────────────────────
    op.create_table(
        "usage_counters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("feature", sa.String(100), nullable=False),
        sa.Column("period_key", sa.String(20), nullable=False),
        sa.Column("count", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("user_id", "feature", "period_key", name="uq_usage_counters"),
    )
    op.create_index("ix_usage_counters_user_feature", "usage_counters", ["user_id", "feature"])

    # ── audit_log (append-only: sem UPDATE/DELETE via API) ────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("actor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("before", JSONB),
        sa.Column("after", JSONB),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"])
    op.create_index("ix_audit_log_actor", "audit_log", ["actor_user_id"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])

    # ── seed planos padrão ─────────────────────────────────────────────────────
    op.execute("""
        INSERT INTO plans (code, name, price_brl, features, limits) VALUES
        ('free', 'Free', 0,
         '{"risk_score": false, "due_diligence_pdf": false, "export": false,
           "calculator": false, "portfolio": false, "realtime_alerts": false,
           "whatsapp_channel": false, "ask": false, "price_forecast": false, "api_access": false}',
         '{"alerts_per_day": 5, "watchlists": 2, "dd_reports_per_month": 0, "ask_per_day": 0}'),
        ('pro', 'Pro', 7900,
         '{"risk_score": true, "due_diligence_pdf": false, "export": true,
           "calculator": true, "portfolio": true, "realtime_alerts": true,
           "whatsapp_channel": false, "ask": false, "price_forecast": false, "api_access": false}',
         '{"alerts_per_day": 50, "watchlists": 10, "dd_reports_per_month": 0, "ask_per_day": 0}'),
        ('premium', 'Premium', 19900,
         '{"risk_score": true, "due_diligence_pdf": true, "export": true,
           "calculator": true, "portfolio": true, "realtime_alerts": true,
           "whatsapp_channel": true, "ask": true, "price_forecast": true, "api_access": false}',
         '{"alerts_per_day": 200, "watchlists": 50, "dd_reports_per_month": 5, "ask_per_day": 20}')
    """)

    # Assinatura Free para todos os usuários existentes
    op.execute("""
        INSERT INTO subscriptions (user_id, plan_id)
        SELECT u.id, p.id FROM users u CROSS JOIN plans p WHERE p.code = 'free'
    """)
    op.execute("""
        UPDATE users u
        SET subscription_id = s.id
        FROM subscriptions s
        JOIN plans p ON s.plan_id = p.id
        WHERE s.user_id = u.id AND p.code = 'free'
    """)


def downgrade() -> None:
    op.execute("UPDATE users SET subscription_id = NULL")
    op.drop_column("users", "subscription_id")
    op.drop_column("users", "notification_channels")
    op.drop_column("users", "role")
    op.drop_index("ix_audit_log_created_at", "audit_log")
    op.drop_index("ix_audit_log_actor", "audit_log")
    op.drop_index("ix_audit_log_entity", "audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_usage_counters_user_feature", "usage_counters")
    op.drop_table("usage_counters")
    op.drop_index("ix_subscriptions_user_id", "subscriptions")
    op.drop_table("subscriptions")
    op.drop_table("plans")
