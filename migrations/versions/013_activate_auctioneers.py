"""Migration 013: activa tos_compliant para leiloeiros validados (Mega, Zuk)."""
from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE banks SET tos_compliant = true WHERE code IN ('mega', 'zuk')")


def downgrade() -> None:
    op.execute("UPDATE banks SET tos_compliant = false WHERE code IN ('mega', 'zuk')")
