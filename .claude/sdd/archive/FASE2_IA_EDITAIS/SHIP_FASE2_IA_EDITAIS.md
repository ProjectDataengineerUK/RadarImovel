# SHIP: Fase 2 — IA nos Editais

| Attribute | Value |
|-----------|-------|
| **Feature** | FASE2_IA_EDITAIS |
| **BUILD_REPORT** | `.claude/sdd/reports/BUILD_REPORT_FASE2_IA_EDITAIS.md` |
| **Shipped** | 2026-06-08 |
| **Commit** | `eb6a606` |
| **Status** | ✅ SHIPPED |

---

## O que foi entregue

Pipeline de leitura automática de editais de imóveis da Caixa com IA generativa:

- **`edital_extractor.py`** — download do PDF do edital do GCS, extração de texto nativo, envio para Gemini (Vertex AI) com `response_schema` estruturado
- **Score enriquecido** (`calculate_enriched_score`) — pontuação adicional baseada em dados do edital: ocupação real, dívidas, ônus, benfeitorias
- **Pipeline assíncrono** via Pub/Sub `edital-events` → Cloud Run Job `radar-process-editais`
- **Idempotência** garantida por unique index parcial + `done_idempotent` no job
- **Reprocessamento manual** via `POST /admin/reprocess-edital/{property_id}`
- **Frontend** com seção `EditalSection` que renderiza dados extraídos (graceful degradation quando não processado)
- **Infra** expandida: tópico `edital-events` + DLQ + bucket `radar-imovel-docs` + IAM `aiplatform.user`

---

## Métricas finais

| Métrica | Valor |
|---------|-------|
| Arquivos do manifesto | 25/25 |
| Testes Fase 2 | 20/20 pass |
| Suíte total (exceto test_api_properties) | 61/61 pass |
| Lint (ruff) | ✅ Pass |
| Frontend `tsc --noEmit` | ✅ Pass |
| `terraform fmt` | ✅ Pass |

---

## Lições aprendidas

### O que funcionou bem

1. **`response_schema` do Gemini** — forçar o modelo a retornar JSON estruturado com schema Pydantic eliminou pós-processamento frágil de texto livre.
2. **Graceful degradation no frontend** — `edital_processed=false` + `edital=null` permite que o MVP funcione mesmo para imóveis ainda não processados, sem erro visível ao usuário.
3. **Score básico preservado** — `calculate_score()` da Fase 1 não foi alterado; o score enriquecido é aditividade pura. Zero regressão.
4. **`StrEnum` (Python 3.12)** — substituir `str, Enum` por `StrEnum` simplificou serialização Pydantic v2 e satisfez o ruff `UP042` sem overhead.

### O que custou tempo

1. **`model_validator` vs `field_validator`** — a derivação de `total_debt_estimate` precisou migrar de `field_validator(after)` para `model_validator(after)` para rodar mesmo quando o campo está ausente no JSON do Gemini.
2. **`_parse_decimal` tolerante** — o Gemini retorna números em formato JSON nativo *ou* string BR (`R$ 50.000,00`). O parser precisou tratar ambos, o que não estava previsto no DESIGN.
3. **Numeração da migration** — o DEFINE referenciava `002_edital_processing` mas `002` e `003` já existiam no repo pós-Fase 1. Resultado: migration criada como `004`.

### Surpresas positivas

- **Confiança do Gemini > 0.85** nos PDFs nativos de teste — muito acima do threshold de 0.60 definido no DEFINE.
- **Fallback Pro** (`GEMINI_FALLBACK_MODEL`) pode ser ativado sem redeploy via env var — design correto para operação.

---

## Dívida técnica conhecida

| Item | Prioridade | Descrição |
|------|-----------|-----------|
| Editais escaneados (OCR) | Alta | PDFs escaneados exigem Document AI; não implementado — Gemini falha com `confidence < 0.30` |
| Validação A-001 em produção | Alta | Confirmar que editais reais da Caixa têm texto nativo (não escaneado) |
| Cloud Scheduler para `process-editais` | Média | Job existe no Terraform mas não tem scheduler; roda apenas via Pub/Sub push |

---

## Arquivos arquivados

- `BRAINSTORM_FASE2_IA_EDITAIS.md`
- `DEFINE_FASE2_IA_EDITAIS.md`
- `DESIGN_FASE2_IA_EDITAIS.md` (status atualizado para `Built / Complete`)
- `BUILD_REPORT_FASE2_IA_EDITAIS.md`
