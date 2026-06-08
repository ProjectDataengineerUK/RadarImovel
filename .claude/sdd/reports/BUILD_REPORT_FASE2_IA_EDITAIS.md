# BUILD REPORT: Fase 2 — IA nos Editais

| Attribute | Value |
|-----------|-------|
| **Feature** | FASE2_IA_EDITAIS |
| **DESIGN** | `.claude/sdd/features/DESIGN_FASE2_IA_EDITAIS.md` |
| **Date** | 2026-06-08 |
| **Status** | COMPLETE |

## Summary

| Metric | Value |
|--------|-------|
| Arquivos do manifesto | 25/25 |
| CREATE | 11 (inclui `extraction_ocupado.json` extra para os testes de integração) |
| MODIFY | 14 |
| Lint (ruff) nos arquivos tocados | Pass |
| Testes Fase 2 (unit + integração) | 20/20 pass |
| Suíte completa (exceto `test_api_properties.py`) | 61/61 pass |
| Frontend `tsc --noEmit` | Pass |
| `terraform fmt` (arquivos tocados) | Pass |

## Status por arquivo

### Backend Python

| # | Arquivo | Ação | Status |
|---|---------|------|--------|
| 1 | `app/schemas/edital.py` | CREATE | criado |
| 2 | `app/connectors/caixa/edital_extractor.py` | CREATE | criado |
| 3 | `app/agents/score_agent.py` | MODIFY | modificado — `calculate_enriched_score()` adicionado, `calculate_score()` preservado |
| 4 | `app/core/config.py` | MODIFY | modificado — settings Vertex/Pub-Sub/editais + pesos do score |
| 5 | `app/api/routes/properties.py` | MODIFY | modificado — `edital_processed` + bloco `edital` |
| 6 | `app/api/routes/admin.py` | MODIFY | modificado — `POST /admin/reprocess-edital/{property_id}` |
| 7 | `app/models/document.py` | MODIFY | modificado — 4 colunas de controle mapeadas |
| 9 | `jobs/process_editais.py` | CREATE | criado — entrypoint Cloud Run Job |
| — | `jobs/collect_caixa.py` | MODIFY | modificado — publica `edital-events` ao criar Property com `edital_url` |
| 10 | `pyproject.toml` | MODIFY | modificado — `google-cloud-aiplatform>=1.60` no extra `job` |

### Database

| # | Arquivo | Ação | Status |
|---|---------|------|--------|
| 8 | `migrations/versions/004_edital_processing.py` | CREATE | criado — 4 colunas + índice parcial + unique parcial de edital |

> Nota de versionamento: a migration é a **004** (`down_revision="003"`), não a "002" referida no DEFINE — `002` e `003` já existiam no repo (vide nota no DESIGN).

### Infra Terraform

| # | Arquivo | Ação | Status |
|---|---------|------|--------|
| 11 | `infra/terraform/pubsub.tf` | MODIFY | tópico `edital-events` + DLQ + subscription (ack 120s, retry 30–600s) |
| 12 | `infra/terraform/iam.tf` | MODIFY | binding `roles/aiplatform.user` para `job_sa` |
| 13 | `infra/terraform/cloud_run.tf` | MODIFY | job `radar-process-editais` (timeout 600s, max_retries 1) |
| 14 | `infra/terraform/variables.tf` | MODIFY | `vertex_location`, `gemini_model`, `gcs_bucket_docs` |
| 15 | `infra/terraform/cloud_storage.tf` | MODIFY | bucket `radar-imovel-docs` (uniform access, privado) |
| — | `infra/terraform/main.tf` | MODIFY | habilita `aiplatform.googleapis.com` |

### Frontend Next.js

| # | Arquivo | Ação | Status |
|---|---------|------|--------|
| 16 | `frontend/lib/types.ts` | MODIFY | tipos `Edital`, `Encumbrance`, `PropertyDetailResponse`, campos opcionais em `Property` |
| 17 | `frontend/components/EditalSection.tsx` | CREATE | criado — dark theme, graceful degradation |
| 18 | `frontend/app/imoveis/[id]/page.tsx` | MODIFY | renderiza `EditalSection` se `edital_processed` |
| — | `frontend/hooks/useProperties.ts` | MODIFY | `useProperty` agora tipado como `PropertyDetailResponse` |

### Testes

| # | Arquivo | Ação | Status |
|---|---------|------|--------|
| 19 | `tests/unit/agents/test_enriched_score.py` | CREATE | criado — 6 testes |
| 20 | `tests/unit/connectors/test_edital_extractor.py` | CREATE | criado — 8 testes |
| 21 | `tests/integration/test_process_editais.py` | CREATE | criado — 6 testes (happy path, idempotência, 404, evento, ignore, low-conf) |
| 22 | `tests/fixtures/editais/edital_livre.pdf` | CREATE | criado — PDF 1.4 válido, texto nativo |
| 23 | `tests/fixtures/editais/edital_ocupado_divida.pdf` | CREATE | criado — PDF 1.4 válido, texto nativo |
| 24 | `tests/fixtures/editais/extraction_livre.json` | CREATE | criado — ground-truth livre |
| — | `tests/fixtures/editais/extraction_ocupado.json` | CREATE | criado — ground-truth ocupado (usado nos testes de integração) |
| 25 | `tests/conftest.py` | MODIFY | fixtures `mock_vertex`, `mock_gcs`, `document_factory` |

## Notas de implementação

- **Score básico preservado.** `calculate_score()` permanece intacto (Fase 1 / fallback). Os pesos do score básico (`score_discount_max_points=60`, `score_occupancy_bonus=40`) não foram alterados para não regredir a coleta atual; os pesos enriquecidos são settings novas e separadas (`score_*_enriched_*`, `score_debt_penalty_max`, etc.).
- **Parser decimal tolerante.** `_parse_decimal` aceita número JSON nativo (caminho normal do `response_schema`) e string em formato BR (`R$ 50.000,00`) ou ISO (`50000.00`), retornando `None` em valor inválido em vez de quebrar a validação.
- **Derivação de dívida** migrada de `field_validator(after)` para `model_validator(after)` para rodar mesmo quando `total_debt_estimate` está ausente no JSON.
- **Idempotência.** `process_message` faz `done_idempotent` quando o Document já está `done` (sem reprocessar, sem republicar). Unique index parcial em `(property_id, document_type='edital')` é a rede de segurança contra corrida; `_get_or_create_document` trata `IntegrityError`.
- **Enums** convertidos para `StrEnum` (Python 3.12) para satisfazer o ruff `UP042`, mantendo a mesma serialização Pydantic v2.
- **Graceful degradation.** API retorna `edital_processed=false` e `edital=null` quando não há Document `done`; o frontend oculta a seção sem erro.

## Como testar localmente

```bash
# --- ambiente (já existe .venv no repo) ---
.venv/bin/python -m pip install -e ".[job,dev]"     # inclui google-cloud-aiplatform

# --- lint ---
.venv/bin/ruff check app/ jobs/ tests/

# --- testes Fase 2 ---
.venv/bin/python -m pytest tests/unit/agents/test_enriched_score.py \
    tests/unit/connectors/test_edital_extractor.py \
    tests/integration/test_process_editais.py -v

# --- suíte completa (test_api_properties.py exige extra "api": fastapi) ---
.venv/bin/python -m pip install -e ".[api]"
.venv/bin/python -m pytest

# --- migration (requer DATABASE_URL apontando para Postgres) ---
alembic upgrade head        # aplica 004_edital_processing

# --- frontend ---
cd frontend && npx tsc --noEmit
```

> A suíte roda em SQLite in-memory; os índices parciais (`postgresql_where`) só existem no Postgres via migration 004 e não interferem nos testes.

## Próximos passos operacionais

1. **Validar A-001 / A-003 (recomendado antes do rollout):**
   - Baixar 5–10 PDFs reais de editais da Caixa e confirmar texto nativo vs. escaneado.
   - PoC de 10 linhas confirmando `Part.from_uri(gcs_uri, mime_type="application/pdf")` sem File API.
2. **Provisionar infra:**
   ```bash
   cd infra/terraform
   terraform init
   terraform plan    # revisar: edital-events (+DLQ+sub), bucket radar-imovel-docs,
                     # job radar-process-editais, IAM aiplatform.user, API aiplatform
   terraform apply
   ```
   - Pré-existe um problema de estilo em `secret_manager.tf` (`replication { auto {} }`) detectado pelo `terraform validate` local; é anterior a esta fase e não pertence ao manifesto da Fase 2. Corrigir para `replication { auto {} }` em linhas separadas se o validate bloquear o apply.
3. **CI/CD (Cloud Build / deploy.yml):**
   - Garantir que a imagem `Dockerfile.job` inclua o extra `job` (já traz `google-cloud-aiplatform`).
   - Adicionar deploy do job `radar-process-editais` e suas env vars: `VERTEX_LOCATION`, `GEMINI_MODEL`, `GCS_BUCKET_DOCS`, `PUBSUB_TOPIC_EDITAIS`, `PUBSUB_SUB_EDITAIS`, `PUBSUB_PROJECT_ID`.
   - Rodar `radar-migrate` (alembic upgrade head) antes da primeira execução do job de editais.
4. **Cloud Scheduler:** apontar um trigger para executar `radar-process-editais` periodicamente (ou disparar por push da subscription, conforme padrão da Fase 1) drenando `edital-events-sub` em lotes de `edital_batch_size` (default 50).
5. **Observabilidade:** monitorar logs `editais.done` (`extraction_confidence`, `model_used`, `duration_ms`) e a profundidade de `edital-events-dlq`. Habilitar o fallback Pro setando `GEMINI_FALLBACK_MODEL=gemini-1.5-pro` (sem deploy de código) caso a taxa de `confidence < 0.60` seja alta.
