"""Adiciona scraping_strategy a banks e gerencia ativação por banco (Fase 3).

Por padrão mantém apenas Caixa ativa; os demais bancos são habilitados
manualmente (UPDATE banks SET active=true) à medida que cada connector é
validado em produção.

Revision ID: 005
Revises: 004
Create Date: 2026-06-08
"""
import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

# Estratégia de coleta por banco (informativa; orienta operação/observabilidade).
STRATEGIES = {
    "caixa": "csv_uf_playwright",
    "bb": "html_portal_httpx",
    "brb": "html_oficial+json_resale",
    "bnb": "html+pdf_relacao",
    "basa": "html_indice+pdf_edital",
    "banrisul": "html_listagem",
    "banestes": "html_indice+pdf_edital",
}


def upgrade() -> None:
    op.add_column(
        "banks",
        sa.Column("scraping_strategy", sa.String(length=100), nullable=True),
    )
    conn = op.get_bind()
    for code, strategy in STRATEGIES.items():
        conn.execute(
            sa.text("UPDATE banks SET scraping_strategy = :s WHERE code = :c"),
            {"s": strategy, "c": code},
        )
    # Caixa permanece a única ativa por padrão; demais habilitados após validação.
    conn.execute(sa.text("UPDATE banks SET active = false WHERE code != 'caixa'"))
    conn.execute(sa.text("UPDATE banks SET active = true WHERE code = 'caixa'"))


def downgrade() -> None:
    op.drop_column("banks", "scraping_strategy")
