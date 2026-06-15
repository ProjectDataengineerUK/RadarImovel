"""Migration 018: ativa todas as fontes pendentes.

- BNB: active=false → active=true
- Leiloeiros (Fidalgo, Frazão, Sodré, TJ-SP): tos_compliant=false → true (validação jurídica concluída)
- Lance Certo e Superleilões: seed na tabela banks (ausentes desde Fase 5)

Revision ID: 018
Revises: 017
Create Date: 2026-06-15
"""
from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Ativa BNB (estava inactive desde seed inicial)
    op.execute("UPDATE banks SET active = true WHERE code = 'bnb'")

    # 2. Libera tos_compliant nos leiloeiros já seedados
    op.execute("""
        UPDATE banks
        SET tos_compliant = true
        WHERE code IN ('fidalgo', 'frazao', 'sodre', 'tjsp')
    """)

    # 3. Seed: Lance Certo e Superleilões (adicionados como conectores na Fase 5, sem row no banco)
    op.execute("""
        INSERT INTO banks (id, code, name, active, source_type, tos_compliant)
        VALUES
          (gen_random_uuid(), 'lance_certo',  'Lance Certo',  true, 'auctioneer', true),
          (gen_random_uuid(), 'superleiloes', 'Superleilões', true, 'auctioneer', true)
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("UPDATE banks SET active = false WHERE code = 'bnb'")
    op.execute("""
        UPDATE banks
        SET tos_compliant = false
        WHERE code IN ('fidalgo', 'frazao', 'sodre', 'tjsp')
    """)
    op.execute("DELETE FROM banks WHERE code IN ('lance_certo', 'superleiloes')")
