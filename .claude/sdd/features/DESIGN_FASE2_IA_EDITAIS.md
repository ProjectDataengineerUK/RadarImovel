# DESIGN: Fase 2 — IA nos Editais (Radar Imóvel)

> Arquitetura técnica do pipeline assíncrono que lê PDFs de editais da Caixa com Gemini 2.0 Flash via Vertex AI, extrai 13 campos estruturados com `response_schema` Pydantic e enriquece o score de oportunidade de 2 para 8+ sinais.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FASE2_IA_EDITAIS |
| **Date** | 2026-06-08 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_FASE2_IA_EDITAIS.md](./DEFINE_FASE2_IA_EDITAIS.md) |
| **BRAINSTORM** | [BRAINSTORM_FASE2_IA_EDITAIS.md](./BRAINSTORM_FASE2_IA_EDITAIS.md) |
| **Status** | Ready for Build |
| **Confidence** | 0.92 — abordagem A do brainstorm, stack GCP consolidada na Fase 1, padrão de Cloud Run Job reutilizado |

> **Nota de versionamento de migration:** o DEFINE referencia "migration 002", porém as migrations `002_add_zipcode_photo` e `003_seed_banks` já existem no repositório. A migration desta fase é a **004** (`004_edital_processing.py`). Onde o DEFINE diz "002", leia-se "004".

---

## 1. Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    RADAR IMÓVEL — FASE 2: IA NOS EDITAIS                       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────┐   ┌───────────────┐   ┌──────────────────────────────┐     │
│  │   Cloud       │──▶│   Pub/Sub      │──▶│  Cloud Run Job               │     │
│  │  Scheduler    │   │ collect-trigger│   │  collect_caixa.py (Fase 1)   │     │
│  │  (3x/dia)     │   └───────────────┘   │  + 3 linhas: publica edital  │     │
│  └──────────────┘                        └──────────┬───────────────────┘     │
│                                                      │ Property nova c/         │
│                                                      │ edital_url preenchida    │
│                                          ┌───────────▼───────────────┐         │
│                                          │  Pub/Sub: edital-events    │  NOVO   │
│                                          │ {property_id, edital_url,  │         │
│                                          │  bank_id}                  │         │
│                                          └───────────┬───────────────┘         │
│                                                      │ pull subscription        │
│                                          ┌───────────▼───────────────────────┐ │
│                                          │  Cloud Run Job                     │ │
│                                          │  process_editais.py        NOVO    │ │
│                                          │  1. idempotência (status=done?)    │ │
│                                          │  2. Document → processing          │ │
│                                          │  3. download PDF (retry 3x)        │ │
│                                          │  4. upload GCS editais/...         │ │
│                                          │  5. Gemini 2.0 Flash + schema      │─┼──┐
│                                          │  6. validar EditaisExtraction      │ │  │
│                                          │  7. persistir ai_summary + status  │ │  │
│                                          │  8. recalcular score + risk_level  │ │  │
│                                          │  9. publica property-events        │ │  │
│                                          └───────────┬───────────────┬───────┘ │  │
│                                                      │               │         │  ▼
│              ┌───────────────────────────────────────▼──┐  ┌─────────▼──────┐  │ ┌────────────────┐
│              │  Cloud SQL PostgreSQL                     │  │ Pub/Sub:       │  │ │ Vertex AI      │
│              │  documents (+ processing_* cols, mig 004) │  │ property-events│  │ │ Gemini 2.0     │
│              │  properties (opportunity_score, risk_lvl) │  │ {edital_       │  │ │ Flash          │
│              └──────────────────┬────────────────────────┘  │  processed}    │  │ │ (PDF via       │
│                                 │                           └────────┬───────┘  │ │  Part.from_uri │
│              ┌──────────────────▼─────────┐                          │          │ │  GCS)          │
│              │  FastAPI /properties/{id}  │              ┌───────────▼───────┐  │ └────────────────┘
│              │  + edital_processed +      │              │ process_alerts.py │  │
│              │    edital{} payload        │              │ (Fase 1, reusa)   │  │
│              └──────────────────┬─────────┘              │ msg enriquecida   │  │
│                                 │                        └───────────┬───────┘  │
│              ┌──────────────────▼─────────┐                          │          │
│              │  Next.js — card do imóvel  │              ┌───────────▼───────┐  │
│              │  seção "Edital"            │              │  Telegram Bot     │  │
│              │  (graceful degradation)    │              │  alerta c/ dívidas│  │
│              └────────────────────────────┘              └───────────────────┘  │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Componentes (novos / modificados)

| Componente | Estado | Propósito | Tecnologia |
|------------|--------|-----------|------------|
| `collect_caixa.py` | MODIFICAR | Publica `edital-events` ao criar Property com `edital_url` | Python, google-cloud-pubsub |
| Pub/Sub `edital-events` | NOVO | Desacopla coleta do processamento de editais | GCP Pub/Sub + DLQ |
| `process_editais.py` | NOVO | Download PDF → GCS → Gemini → persiste → recalcula score | Python, Cloud Run Job |
| `edital_extractor.py` | NOVO | Cliente Vertex AI + schema `EditaisExtraction` + prompt | Python, google-cloud-aiplatform |
| Vertex AI Gemini 2.0 Flash | NOVO (externo) | Extração estruturada multimodal do PDF | Vertex AI `response_schema` |
| `score_agent.py` | MODIFICAR | `calculate_enriched_score()` com 8+ sinais | Python |
| Migration 004 | NOVO | Campos de controle em `documents` | Alembic |
| `properties.py` (route) | MODIFICAR | Expõe `edital_processed` + bloco `edital` | FastAPI |
| Card do imóvel | MODIFICAR | Seção "Edital" com graceful degradation | Next.js / TypeScript |

---

## 2. File Manifest

### Backend — Python

| # | Arquivo | Action | Agente | Descrição |
|---|---------|--------|--------|-----------|
| 1 | `app/connectors/caixa/edital_extractor.py` | CREATE | @ai-prompt-specialist-gcp | Cliente Vertex AI + schema `EditaisExtraction` + system/user prompt + `extract_from_gcs(uri)` |
| 2 | `app/agents/score_agent.py` | MODIFY | @python-developer | Adiciona `calculate_enriched_score()` (8+ sinais) preservando `calculate_score()` básico como fallback |
| 3 | `jobs/process_editais.py` | CREATE | @python-developer | Entrypoint Cloud Run Job: pull `edital-events`, download/upload/extração/persistência/score/publish |
| 4 | `app/models/document.py` | MODIFY | @database-reviewer | Mapeia as 4 colunas novas (`processing_status`, `processing_error`, `processed_at`, `extraction_confidence`) |
| 5 | `app/core/config.py` | MODIFY | @python-developer | Settings novas: `pubsub_topic_editais`, `vertex_*`, `gcs_bucket_docs`, `edital_*`, pesos do score |
| 6 | `app/api/routes/properties.py` | MODIFY | @python-developer | Inclui `edital_processed` + bloco `edital` no response de `GET /properties/{id}` |
| 7 | `app/api/routes/admin.py` | MODIFY | @python-developer | `POST /admin/reprocess-edital/{property_id}` (COULD — republica em `edital-events`) |
| 8 | `app/schemas/edital.py` | CREATE | @python-developer | Pydantic de saída da API para o bloco `edital` (separa contrato API do schema do LLM) |

### Migrations — Alembic

| # | Arquivo | Action | Agente | Descrição |
|---|---------|--------|--------|-----------|
| 9 | `migrations/versions/004_edital_processing.py` | CREATE | @database-reviewer | Adiciona 4 colunas de controle + índice parcial em `documents`; `downgrade` reversível |

### Infra — Terraform

| # | Arquivo | Action | Agente | Descrição |
|---|---------|--------|--------|-----------|
| 10 | `infra/terraform/pubsub.tf` | MODIFY | @gcp-data-architect | Tópico `edital-events` + DLQ + subscription com retry/backoff |
| 11 | `infra/terraform/iam.tf` | MODIFY | @gcp-data-architect | Binding `roles/aiplatform.user` para `job_sa` |
| 12 | `infra/terraform/cloud_run.tf` | MODIFY | @gcp-data-architect | Job `radar-process-editais` (timeout 600s, max_retries 1) |
| 13 | `infra/terraform/variables.tf` | MODIFY | @gcp-data-architect | `vertex_location`, `gemini_model`, `gcs_bucket_docs` |
| 14 | `infra/terraform/cloud_storage.tf` | MODIFY | @gcp-data-architect | Garante bucket `radar-imovel-docs` (prefix `editais/`); reusa se já provisionado |

### Frontend — Next.js

| # | Arquivo | Action | Agente | Descrição |
|---|---------|--------|--------|-----------|
| 15 | `frontend/app/imoveis/[id]/page.tsx` | MODIFY | @typescript-reviewer | Renderiza seção "Edital" se `edital_processed`; caso contrário oculta sem erro |
| 16 | `frontend/components/EditalSection.tsx` | CREATE | @typescript-reviewer | Componente da seção edital: praças, pagamento, ocupação, dívidas, ônus, risco |
| 17 | `frontend/lib/types.ts` | MODIFY | @typescript-reviewer | Tipos `Edital`, `Encumbrance`, `edital_processed`, campos opcionais |

### Dependências

| # | Arquivo | Action | Agente | Descrição |
|---|---------|--------|--------|-----------|
| 18 | `pyproject.toml` | MODIFY | @python-developer | Adiciona `google-cloud-aiplatform>=1.60` ao extra `job` |

### Testes

| # | Arquivo | Action | Agente | Descrição |
|---|---------|--------|--------|-----------|
| 19 | `tests/unit/agents/test_enriched_score.py` | CREATE | @python-developer | Casos do score enriquecido (livre/sem dívida vs. ocupado/IPTU R$50k) |
| 20 | `tests/unit/connectors/test_edital_extractor.py` | CREATE | @python-developer | Valida schema, parsing do `response.parsed`, fallback de campos ausentes (mock Vertex AI) |
| 21 | `tests/integration/test_process_editais.py` | CREATE | @python-developer | Fluxo end-to-end com mock Vertex AI + GCS + httpx; idempotência (AT-002) e 404 (AT-004) |
| 22 | `tests/fixtures/editais/edital_livre.pdf` | CREATE | @python-developer | Fixture PDF de imóvel livre sem dívida |
| 23 | `tests/fixtures/editais/edital_ocupado_divida.pdf` | CREATE | @python-developer | Fixture PDF de imóvel ocupado com IPTU alto |
| 24 | `tests/fixtures/editais/extraction_livre.json` | CREATE | @python-developer | Ground-truth esperado para o mock do Gemini |
| 25 | `tests/conftest.py` | MODIFY | @python-developer | Fixtures `mock_vertex`, `mock_gcs`, `document_factory` |

**Total: 25 arquivos (9 CREATE / 16 MODIFY).**

### Agent Assignment Rationale

| Agente | Arquivos | Justificativa |
|--------|----------|---------------|
| @ai-prompt-specialist-gcp | 1 | Prompt e `response_schema` do Gemini são o coração de qualidade da extração |
| @python-developer | 2,3,5,6,7,8,15(API contract),18,19-25 | Job, score, config, rotas, testes |
| @database-reviewer | 4,9 | Migration e mapeamento de colunas; idempotência e índice parcial |
| @gcp-data-architect | 10-14 | Terraform: Pub/Sub, IAM Vertex AI, Cloud Run Job, bucket |
| @typescript-reviewer | 15,16,17 | Seção edital no dashboard com graceful degradation |

---

## 3. Schema Changes — Migration 004

`migrations/versions/004_edital_processing.py` (`down_revision = "003"`):

```python
"""Edital processing control columns on documents.

Revision ID: 004
Revises: 003
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa

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
```

**`properties` — sem migration necessária.** `risk_level` (`String(20)`) e `opportunity_score` (`SmallInteger`) já existem desde a Fase 1 e aceitam `low/medium/high` e 0–100. `auction_date`, `auctioneer_name`, `appraisal_value`, `edital_number` também já existem — o job pode atualizá-los com o dado mais preciso do edital quando ausentes na planilha.

**Mapeamento em `app/models/document.py` (item 4):**

```python
processing_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
processing_error: Mapped[str | None] = mapped_column(Text)
processed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
```

---

## 4. Pydantic Schema do Gemini — `EditaisExtraction`

Em `app/connectors/caixa/edital_extractor.py`. Todos os campos opcionais usam `None` como default para tolerar editais incompletos (Pydantic não penaliza campo ausente; o score trata `None`).

```python
from __future__ import annotations
from decimal import Decimal
from datetime import date
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class OccupancyDetail(str, Enum):
    livre = "livre"
    ocupado_com_acao_judicial = "ocupado_com_acao_judicial"
    ocupado_sem_acao = "ocupado_sem_acao"
    locado = "locado"
    unknown = "unknown"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class EncumbranceType(str, Enum):
    iptu = "iptu"
    condominio = "condominio"
    hipoteca = "hipoteca"
    outros = "outros"


class Encumbrance(BaseModel):
    type: EncumbranceType
    amount_approx: Decimal | None = None       # R$, None se não declarado
    description: str = ""


class EditaisExtraction(BaseModel):
    """Saída estruturada do Gemini 2.0 Flash para um edital da Caixa.
    Espelha o Data Contract do DEFINE (13 campos de negócio + 2 de meta)."""

    edital_number: str | None = None
    auction_date_1st: date | None = None        # 1ª praça
    auction_date_2nd: date | None = None         # 2ª praça (se houver)
    minimum_bid_1st: Decimal | None = None        # lance mínimo 1ª praça (R$)
    minimum_bid_2nd: Decimal | None = None        # lance mínimo 2ª praça (R$)
    appraisal_value: Decimal | None = None        # valor de avaliação oficial (R$)
    payment_modalities: list[str] = Field(default_factory=list)
    # itens válidos: vista | financiamento_caixa | fgts | carta_credito | consorcio
    occupancy_detail: OccupancyDetail = OccupancyDetail.unknown
    encumbrances: list[Encumbrance] = Field(default_factory=list)
    total_debt_estimate: Decimal | None = None    # soma de dívidas herdáveis (R$)
    registration_number: str | None = None         # matrícula no cartório
    auctioneer_name: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    # válidos: ocupado | divida_elevada | onus_registrado | area_irregular | leilao_judicial
    risk_level: RiskLevel = RiskLevel.medium       # estimativa do Gemini; recalculada por nós
    extraction_confidence: float = Field(0.0, ge=0.0, le=1.0)

    @field_validator("total_debt_estimate", mode="after")
    @classmethod
    def derive_total_debt(cls, v, info):
        """Se o Gemini não somou, deriva da lista de encumbrances."""
        if v is not None:
            return v
        encs = info.data.get("encumbrances") or []
        known = [e.amount_approx for e in encs if e.amount_approx is not None]
        return sum(known) if known else None
```

> **`response_schema`:** o Vertex AI aceita o JSON Schema gerado por `EditaisExtraction.model_json_schema()` (com `response_mime_type="application/json"`). O SDK retorna `response.parsed`/`response.text`; validamos com `EditaisExtraction.model_validate_json(response.text)`. `Decimal` é serializado como `number` no schema do Gemini — converter no validator se vier string.

---

## 5. Prompt do Gemini

Estrutura em `edital_extractor.py`. Modelo configurável (`settings.gemini_model`, default `gemini-2.0-flash`).

### System prompt

```text
Você é um analista jurídico-imobiliário especializado em editais de leilão e venda
direta da Caixa Econômica Federal. Sua tarefa é extrair informações estruturadas de
um edital em PDF para alimentar um score de oportunidade de investimento.

REGRAS:
1. Extraia SOMENTE informações explícitas no documento. NUNCA invente valores.
2. Se um campo não constar no edital, retorne null (ou lista vazia para campos de lista).
   Campo ausente é esperado e não é erro — não force um valor aproximado.
3. Valores monetários: número decimal em reais, sem "R$", sem separador de milhar
   (ex: 50000.00). Datas: formato ISO YYYY-MM-DD.
4. occupancy_detail: classifique a situação real de ocupação descrita no edital.
   Use "unknown" apenas se o edital for omisso.
5. encumbrances: liste cada ônus/dívida herdável pelo arrematante (IPTU, condomínio,
   hipoteca). NÃO inclua o lance mínimo nem custas de leilão.
6. total_debt_estimate: some apenas dívidas que o ARREMATANTE assume. Se o edital
   declarar que débitos são quitados com o produto da arrematação, retorne 0.
7. risk_level: classifique low/medium/high considerando ocupação, dívidas vs.
   avaliação e ônus registrados.
8. risk_flags: marque "ocupado" se não-livre, "divida_elevada" se dívidas > 20% da
   avaliação, "onus_registrado" se houver hipoteca/penhora, "area_irregular" se houver
   menção a divergência de área/averbação pendente, "leilao_judicial" se judicial.
9. extraction_confidence: 0.0–1.0 refletindo quão legível/completo era o documento.
   PDF escaneado de baixa qualidade ou texto truncado → confiança baixa.

Responda EXCLUSIVAMENTE com o JSON no schema fornecido. Sem comentários, sem markdown.
```

### User prompt

```text
Extraia os campos do edital anexo (imóvel {property_external_code}, {city}/{state}).
Tipo de venda informado na coleta: {sale_modality}.
Avaliação informada na planilha (referência, pode divergir): R$ {appraisal_hint}.

Anexo: <PDF via Part.from_uri(gcs_uri, mime_type="application/pdf")>
```

### Chamada (esqueleto)

```python
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

model = GenerativeModel(settings.gemini_model, system_instruction=SYSTEM_PROMPT)
resp = model.generate_content(
    [Part.from_uri(gcs_uri, mime_type="application/pdf"), user_prompt],
    generation_config=GenerationConfig(
        temperature=0.0,
        response_mime_type="application/json",
        response_schema=EditaisExtraction.model_json_schema(),
    ),
)
extraction = EditaisExtraction.model_validate_json(resp.text)
```

> **Fallback de modelo (OQ-02):** se `extraction.extraction_confidence < settings.gemini_confidence_floor` (default 0.60) **e** `settings.gemini_fallback_model` configurado (default `gemini-1.5-pro`), o extractor reexecuta uma vez com o modelo Pro. Loga `model_used` e ambas as confianças. Desligado por default no MVP (custo); habilitável por env var sem deploy de código.

---

## 6. Score Enriquecido

`app/agents/score_agent.py` (item 2). Range final **0–100**. `calculate_score()` (2 sinais) permanece como fallback quando não há extração (graceful degradation).

### Composição de sinais

| Sinal | Faixa | Fonte | Direção |
|-------|-------|-------|---------|
| `discount_score` | 0–45 | desconto efetivo = `(appraisal − minimum) / appraisal − total_debt/appraisal` | + |
| `occupancy_score` | 0–20 | `occupancy_detail` do edital (mais preciso que a planilha) | + |
| `payment_score` | 0–10 | `payment_modalities` (financiamento +4, fgts +4, vista +2, cap 10) | + |
| `auction_proximity` | 0–5 | dias até `auction_date_1st` (15–60 dias = janela ideal) | + |
| `debt_penalty` | −30–0 | `total_debt_estimate / appraisal_value` | − |
| `risk_flag_penalty` | −20–0 | −7 por flag em `risk_flags` (cap −20) | − |
| `onus_penalty` | −15–0 | −15 se `hipoteca`/`onus_registrado` presente | − |
| `confidence_weight` | fator | mistura score enriquecido com básico por `extraction_confidence` | × |

### Tabela de pontos (`occupancy_score`)

| `occupancy_detail` | Pontos |
|--------------------|--------|
| `livre` | 20 |
| `locado` | 10 |
| `ocupado_sem_acao` | 5 |
| `ocupado_com_acao_judicial` | 0 |
| `unknown` | 8 (neutro) |

### Mistura por confiança

```python
def calculate_enriched_score(property_data: dict, extraction: dict | None) -> tuple[int, str]:
    """Retorna (score 0-100, risk_level). Sem extração → score básico."""
    base = calculate_score(property_data)                      # 0–100 (Fase 1)
    if not extraction:
        return base, _basic_risk(property_data)

    s = (
        _discount_score(property_data, extraction)             # 0–45
        + _occupancy_score(extraction)                          # 0–20
        + _payment_score(extraction)                            # 0–10
        + _auction_proximity(extraction)                        # 0–5
        + _debt_penalty(property_data, extraction)              # −30–0
        + _risk_flag_penalty(extraction)                        # −20–0
        + _onus_penalty(extraction)                             # −15–0
    )
    enriched = max(0, min(100, s))

    # Mistura: baixa confiança → mais peso ao score básico
    conf = float(extraction.get("extraction_confidence") or 0.0)
    final = round(conf * enriched + (1 - conf) * base)

    return int(final), _risk_level(property_data, extraction)
```

`_risk_level`: `high` se `debt_ratio > 0.20` **ou** `onus_registrado` **ou** `ocupado_com_acao_judicial`; `low` se `livre` **e** `debt_ratio < 0.05` **e** sem flags; senão `medium`. Mantém o `risk_level` do Gemini como tiebreaker.

### Casos de exemplo (verificáveis nos testes)

| Caso | Dados | Score básico | Score enriquecido | risk_level |
|------|-------|--------------|-------------------|------------|
| **Imóvel livre sem dívida** | desconto 40%, `livre`, `total_debt=0`, modalidades `[vista,financiamento_caixa,fgts]`, leilão em 25 dias, conf 0.9 | 80 | ~95 (45 desc + 20 ocup + 10 pgto + 5 prox − 0) | `low` (AT-006) |
| **Ocupado com IPTU R$50k** | desconto 40%, avaliação R$200k, `ocupado_com_acao_judicial`, `total_debt=50000` (25% aval), flag `divida_elevada`+`ocupado`, conf 0.85 | 80 | ~30 (desconto efetivo cai p/ ~15% → ~17 + 0 ocup − 30 debt − 14 flags) | `high` (AT-005) |
| **Sem edital processado** | `extraction=None` | 80 | 80 (= básico) | básico (AT-003) |
| **Confiança baixa** | enriquecido 30, básico 80, conf 0.4 | 80 | 60 (0.4×30 + 0.6×80) | medium |

---

## 7. Terraform Changes

### `pubsub.tf` (MODIFY) — novo tópico

```hcl
resource "google_pubsub_topic" "edital_events" {
  name = "edital-events"
}

resource "google_pubsub_topic" "edital_events_dlq" {
  name = "edital-events-dlq"
}

resource "google_pubsub_subscription" "edital_events_sub" {
  name                       = "edital-events-sub"
  topic                      = google_pubsub_topic.edital_events.name
  ack_deadline_seconds       = 120          # Gemini P95 < 60s + margem
  message_retention_duration = "86400s"

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.edital_events_dlq.id
    max_delivery_attempts = 5
  }
  retry_policy {
    minimum_backoff = "30s"
    maximum_backoff = "600s"
  }
}
```

### `iam.tf` (MODIFY) — Vertex AI para o job

```hcl
resource "google_project_iam_member" "job_vertex" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.job_sa.email}"
}
```

> `job_sa` já tem `storage.objectAdmin` (lê o PDF do GCS para o Gemini) e `pubsub.editor` (pull + publish). Só falta `aiplatform.user`.

### `cloud_run.tf` (MODIFY) — novo job

```hcl
resource "google_cloud_run_v2_job" "process_editais" {
  name     = "radar-process-editais"
  location = var.region

  template {
    template {
      service_account = google_service_account.job_sa.email
      max_retries     = 1
      timeout         = "600s"          # lote de editais; Pub/Sub gerencia retry por msg
      containers {
        image   = local.placeholder
        command = ["python", "jobs/process_editais.py"]
      }
    }
  }
  lifecycle { ignore_changes = [template] }
  depends_on = [google_project_service.apis]
}
```

### `variables.tf` (MODIFY)

```hcl
variable "vertex_location" { type = string, default = "us-central1" }
variable "gemini_model"    { type = string, default = "gemini-2.0-flash" }
variable "gcs_bucket_docs" { type = string, default = "radar-imovel-docs" }
```

### `main.tf` — habilitar API

Adicionar `aiplatform.googleapis.com` à lista `google_project_service.apis`.

### `cloud_storage.tf` (MODIFY)

Garantir bucket `radar-imovel-docs` (uniform access, privado). Prefix `editais/{bank}/{state}/{property_id}.pdf` é convenção de código, não recurso Terraform.

---

## 8. Key Decisions

### Decision 1 (OQ-01): Trigger via Pub/Sub `edital-events` publicado pelo coletor

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Resolve** | OQ-01 |

**Context:** Quando publicar a mensagem que dispara o processamento do edital — durante a coleta (opção a) ou via varredura periódica de `documents WHERE status='pending'` (opção b)?

**Choice:** Opção (a). `collect_caixa.py` publica em `edital-events` no momento em que cria uma `Property` nova **com `edital_url` preenchida**.

**Rationale:** Menor latência (atende o SLA de 30 min do DEFINE), acoplamento mínimo reusando o padrão Pub/Sub já consolidado na Fase 1, e custo zero adicional de polling. O coletor já publica em `property-events` no mesmo ponto do código (linha 79-83 de `collect_caixa.py`) — adicionar a publicação de `edital-events` são ~5 linhas, sem nova varredura no banco.

**Implementação no coletor (modificação mínima):**

```python
# após session.flush() do novo Property, dentro do if existing is None:
if prop.edital_url:
    publish_event(
        settings.pubsub_project_id,
        settings.pubsub_topic_editais,            # "edital-events"
        {"property_id": str(prop.id), "edital_url": prop.edital_url,
         "bank_id": str(bank.id)},
    )
```

**Alternatives Rejected:**
1. Varredura periódica (opção b) — adiciona até N minutos de latência e um Cloud Scheduler extra; simplicidade não compensa o custo de SLA.
2. GCS-triggered (upload do PDF dispara Eventarc) — exige que o download aconteça no coletor, acoplando coleta a I/O de PDF e quebrando o isolamento dos jobs.

**Consequences:**
- `process_editais.py` consome via pull subscription `edital-events-sub`.
- Idempotência é obrigatória (Decision 3): o mesmo `property_id` pode chegar mais de uma vez (re-execução do coletor, redelivery do Pub/Sub).
- `process_alerts.py` continua consumindo `property-events`; o job de editais publica `property-events {event_type: "edital_processed"}` ao final para enriquecer o alerta.

---

### Decision 2 (OQ-02): Gemini 2.0 Flash default, Pro como fallback configurável

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Resolve** | OQ-02 |

**Context:** Flash (6x mais barato, menor latência) vs. 1.5 Pro (maior precisão em PDFs complexos).

**Choice:** `gemini-2.0-flash` como default. Fallback opcional para `gemini-1.5-pro` apenas quando `extraction_confidence < gemini_confidence_floor` (0.60) **e** o fallback estiver habilitado por env var. Desligado por default no MVP.

**Rationale:** O budget é R$ 50/mês para 10k editais; Flash custa ~$0.0004/edital (~$4/mês), Pro inviabilizaria o budget se usado sempre. A maioria dos editais da Caixa é texto nativo (assumption A-001), onde Flash já é suficiente. O campo `extraction_confidence` permite triagem: só os editais difíceis (PDF escaneado, layout atípico) acionam o Pro, mantendo o custo médio próximo do Flash.

**Alternatives Rejected:**
1. Pro sempre — estoura o budget (~6x custo) sem ganho na maioria dos editais.
2. Flash sempre, sem fallback — extrações de baixa confiança ficam sem segunda chance; piora qualidade em PDFs escaneados.

**Consequences:**
- 2 settings: `gemini_model`, `gemini_fallback_model`, `gemini_confidence_floor`.
- Log estruturado de `model_used` + `extraction_confidence` por edital para monitorar a taxa de fallback e ajustar o floor.
- Mudar a política não exige deploy de código — só env var no job.

---

### Decision 3: Idempotência por `processing_status` + unique index

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |

**Context:** Jobs Cloud Run e Pub/Sub fazem redelivery; o mesmo edital pode ser processado mais de uma vez (AT-002).

**Choice:** Antes de processar, o job busca `Document(property_id, document_type='edital')`. Se `processing_status == 'done'`, faz **ack** da mensagem e encerra sem reprocessar, sem republicar `property-events`. O unique index parcial (`uq_documents_property_edital`) garante zero duplicação a nível de banco mesmo em corrida.

**Rationale:** Atende AT-002 e o Data Contract ("zero `property_id` duplicados para `document_type=edital`"). A verificação em código evita custo de Vertex AI desnecessário; o índice é a rede de segurança contra concorrência.

**Consequences:**
- Reprocessamento manual (`POST /admin/reprocess-edital/{id}`) reseta `processing_status='pending'` antes de republicar.
- Insert do `Document` usa `ON CONFLICT DO NOTHING` / try-except `IntegrityError` para corridas.

---

### Decision 4: Graceful degradation no score e no dashboard

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |

**Context:** A coleta é mais rápida que o processamento de editais; imóveis recém-criados não têm extração ainda (AT-003).

**Choice:** `calculate_enriched_score(prop, extraction=None)` retorna o score básico da Fase 1. A API retorna `edital_processed: false` e omite o bloco `edital`. O frontend oculta a seção sem erro.

**Rationale:** Garante que o produto funciona em todos os estados do pipeline; nenhum imóvel fica sem score. Atende ao success criterion de degradação graciosa.

---

## 9. Test Plan

### Fixtures (itens 22–25)

| Fixture | Conteúdo | Usado em |
|---------|----------|----------|
| `edital_livre.pdf` | Imóvel livre, sem dívida, modalidades vista+financiamento+fgts | AT-006, score |
| `edital_ocupado_divida.pdf` | Ocupado c/ ação judicial, IPTU R$50k (25% da avaliação), hipoteca | AT-005, score |
| `extraction_livre.json` / `extraction_ocupado.json` | Ground-truth que o `mock_vertex` retorna como `response.text` | unit + integration |

> Fixtures PDF podem ser gerados sinteticamente (reportlab) com o texto representativo, evitando dados reais da Caixa no repositório. O conteúdo deve cobrir os 13 campos.

### Mock Vertex AI (`conftest.py`, item 25)

```python
@pytest.fixture
def mock_vertex(monkeypatch):
    """Substitui GenerativeModel.generate_content por resposta determinística."""
    def _make(json_path: str):
        payload = Path(json_path).read_text()
        class _Resp: text = payload
        def _gen(self, *a, **k): return _Resp()
        monkeypatch.setattr(
            "app.connectors.caixa.edital_extractor.GenerativeModel.generate_content",
            _gen,
        )
    return _make
```

`mock_gcs` faz patch de `storage.Client` (upload no-op, retorna URI fake). Download de PDF via `responses`/`respx` para httpx.

### Testes unitários — `test_enriched_score.py` (item 19)

| Teste | Asserção |
|-------|----------|
| `test_score_livre_sem_divida` | enriquecido > básico; `risk_level == "low"` (AT-006) |
| `test_score_ocupado_divida_alta` | enriquecido < básico; `risk_level == "high"` (AT-005) |
| `test_score_sem_extracao` | `calculate_enriched_score(p, None) == (calculate_score(p), básico)` (AT-003) |
| `test_confidence_blending` | conf 0.4 → final entre básico e enriquecido |
| `test_debt_ratio_threshold` | dívida > 20% aval ⇒ flag `divida_elevada` reflete no penalty |
| `test_score_clamped_0_100` | nunca < 0 nem > 100 |

### Testes unitários — `test_edital_extractor.py` (item 20)

| Teste | Asserção |
|-------|----------|
| `test_schema_valida_json_completo` | `EditaisExtraction.model_validate_json` parseia ground-truth |
| `test_campo_ausente_vira_none` | JSON sem `auctioneer_name` ⇒ `None`, sem ValidationError |
| `test_total_debt_derivado` | `total_debt_estimate=null` + encumbrances ⇒ soma derivada |
| `test_occupancy_enum_invalido_fallback` | valor fora do enum ⇒ tratado/`unknown` |
| `test_decimal_de_string` | `"50000.00"` → `Decimal` |

### Testes de integração — `test_process_editais.py` (item 21)

| Teste | Cenário | Asserção |
|-------|---------|----------|
| `test_happy_path` | Property c/ edital_url, Document inexistente | Document `done`, `ai_summary` com ≥8 campos, `risk_level` atualizado (AT-001) |
| `test_idempotencia` | Document já `done` | Nenhum novo Document; score inalterado; nenhum `property-events` publicado (AT-002) |
| `test_url_404` | download retorna 404 nas 3 tentativas | `processing_status='skipped'`, `processing_error` preenchido, sem crash (AT-004) |
| `test_publica_evento_apos_done` | extração ok | `property-events {event_type:"edital_processed"}` publicado uma vez |
| `test_low_confidence_sem_fallback` | conf 0.4, fallback desligado | mantém Flash, `done`, loga confiança |

### Estratégia geral

| Tipo | Escopo | Ferramentas | Meta |
|------|--------|-------------|------|
| Unit | score enriquecido, schema, prompt builder | pytest, fixtures JSON | 90% das funções de score e extractor |
| Integration | job completo c/ mocks | pytest, monkeypatch, responses, DB de teste | AT-001, AT-002, AT-004 |
| Manual E2E | 1 edital real Caixa → Vertex AI real → score | execução em dev | valida A-001/A-003 antes do rollout |

---

## 10. Data Flow

```text
1. collect_caixa.py cria Property nova com edital_url
   └─ publish edital-events {property_id, edital_url, bank_id}
        ▼
2. process_editais.py (pull edital-events-sub)
   ├─ Document existe e status='done'? → ack + return (idempotência)
   ├─ upsert Document(status='processing')
   ├─ download PDF (httpx, timeout 30s, retry 3x backoff) → 404 persistente? status='skipped'
   ├─ upload GCS: editais/{bank}/{state}/{property_id}.pdf
   ├─ Vertex AI: Gemini Flash(Part.from_uri(gcs_uri), schema) → resp
   │    └─ conf < floor & fallback? → Gemini Pro (1x)
   ├─ EditaisExtraction.model_validate_json(resp.text)
   ├─ Document.ai_summary = json; status='done'; processed_at=now; extraction_confidence
   ├─ Property: opportunity_score, risk_level = calculate_enriched_score(...)
   │            + preenche auction_date/auctioneer/appraisal se nulos
   └─ publish property-events {property_id, event_type:'edital_processed'}
        ▼
3. process_alerts.py (Fase 1) consome property-events
   └─ formata mensagem enriquecida se Document.ai_summary disponível → Telegram
        ▼
4. GET /properties/{id} → edital_processed + bloco edital → card no dashboard
```

---

## Error Handling

| Erro | Estratégia | Status final |
|------|-----------|--------------|
| PDF URL 404/timeout (3x) | retry exponencial; depois marca skipped | `skipped` + `processing_error` |
| Vertex AI 5xx/quota | Pub/Sub nack → redelivery (até 5x) → DLQ | permanece `processing`, depois DLQ |
| `ValidationError` no schema | log + 1 retry com `temperature=0`; persiste raw em `extracted_text` | `failed` |
| PDF escaneado, conf baixa | fallback Pro (se on); senão persiste com conf baixa | `done` (conf < 0.6 sinalizada) |
| Document duplicado (corrida) | `IntegrityError` → ack, trata como já processado | `done` (do vencedor) |
| Property sem edital_url na msg | log warning, ack | — (não cria Document) |

---

## Configuration (novas keys em `app/core/config.py`)

| Key | Default | Descrição |
|-----|---------|-----------|
| `pubsub_topic_editais` | `edital-events` | Tópico que dispara o processamento |
| `pubsub_sub_editais` | `edital-events-sub` | Subscription pull do job |
| `gcs_bucket_docs` | `radar-imovel-docs` | Bucket dos PDFs de editais |
| `vertex_location` | `us-central1` | Região do Vertex AI |
| `gemini_model` | `gemini-2.0-flash` | Modelo default |
| `gemini_fallback_model` | `""` (off) | Modelo de fallback (ex: `gemini-1.5-pro`) |
| `gemini_confidence_floor` | `0.60` | Limiar para acionar fallback |
| `edital_download_timeout_s` | `30` | Timeout do download do PDF |
| `edital_max_retries` | `3` | Tentativas de download |
| `edital_batch_size` | `50` | Máx. de mensagens por execução do job (controle de custo) |
| `score_discount_max_points` | `45` | Peso do desconto no score enriquecido |
| `score_debt_penalty_max` | `30` | Penalidade máxima por dívida |

---

## Observability

| Aspecto | Implementação |
|---------|--------------|
| Logging | structlog com `property_id`, `processing_status`, `extraction_confidence`, `model_used`, `duration_ms` |
| Métrica de qualidade | log por edital permite agregar % com `confidence >= 0.75` (success criterion) |
| Custo | log de `model_used`; alerta de billing GCP a 80% do budget (COULD) |
| Latência | `duration_ms` por edital; meta P95 < 60s |
| DLQ | `edital-events-dlq` inspecionável; alerta se profundidade > 0 |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-08 | design-agent | Versão inicial — 25 arquivos, pipeline Vertex AI Gemini, score enriquecido, migration 004, OQ-01/OQ-02 resolvidos |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_FASE2_IA_EDITAIS.md`

**Validar antes do build (assumptions do DEFINE):**
1. **A-003** — PoC: `Part.from_uri(gcs_uri, mime_type="application/pdf")` funciona sem File API separada (10 linhas).
2. **A-001** — amostra de 5–10 PDFs reais da Caixa para confirmar texto nativo vs. escaneado e calibrar o `gemini_confidence_floor`.
