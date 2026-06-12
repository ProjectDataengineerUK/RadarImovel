# SHIPPED — V2 Onda 4 — Céu Azul

**Data:** 2026-06-12  
**Testes:** 307/307 passando  
**Commits:** onda4 branch → main

---

## Features entregues

### AT-008 — Curva preditiva de desconto (Kaplan-Meier heurístico)

| Arquivo | Status |
|---------|--------|
| `app/prediction/__init__.py` | ✅ Criado |
| `app/prediction/priors.yaml` | ✅ Criado |
| `app/prediction/price_drop.py` | ✅ Criado |
| `app/models/prediction.py` (`PricePrediction`) | ✅ Criado |
| `migrations/versions/012_predictions.py` | ✅ Criado |
| `jobs/predict_drops.py` | ✅ Criado |
| `app/api/routes/properties.py` — endpoint `/predictions` | ✅ Modificado |
| `frontend/components/PriceDropForecast.tsx` | ✅ Criado |
| `tests/unit/test_price_drop.py` | ✅ 12 testes |

**Decisão de design:** blend_weight = min(N / BOOTSTRAP_N, 1.0). Com N < 30, o prior
do banco domina. Com N ≥ 30, a evidência empírica domina completamente. Probabilidade
clampada em [0.0, 1.0].

---

### AT-009 — "Pergunte ao edital" (RAG com citação obrigatória)

| Arquivo | Status |
|---------|--------|
| `app/rag/__init__.py` | ✅ Criado |
| `app/rag/indexer.py` | ✅ Criado |
| `app/rag/chat.py` | ✅ Criado |
| `app/models/prediction.py` (`RagChunk`) | ✅ Criado |
| `app/api/routes/ask.py` | ✅ Criado |
| `app/api/main.py` — router registrado | ✅ Modificado |
| `jobs/process_editais.py` — indexação RAG pós-extração | ✅ Modificado |
| `frontend/components/AskEdital.tsx` | ✅ Criado |
| `tests/unit/test_rag_citations.py` | ✅ 11 testes |
| `tests/integration/test_ask_endpoint.py` | ✅ 7 testes |
| `infra/terraform/vertex.tf` | ✅ Criado |

**Garantia anti-alucinação:** cada `citation.quote` validado server-side via substring
match no chunk referenciado. Citações inválidas são descartadas. Se todas as citações
fornecidas por Gemini forem inválidas, `not_found=True` é retornado.

**Bug corrigido:** `_build_chunk_map` usava `c.id` (PK) em vez de `c.vector_id` como
chave, causando mismatch com as citações geradas pelo Gemini (que recebe `vector_id`
no contexto).

---

### Radar Index — Índice público de deságio

| Arquivo | Status |
|---------|--------|
| `app/models/prediction.py` (`RadarIndex`) | ✅ Criado |
| `jobs/build_radar_index.py` | ✅ Criado |
| `app/api/routes/radar_index.py` | ✅ Criado |
| `app/api/main.py` — router registrado | ✅ Modificado |
| `frontend/app/radar-index/page.tsx` | ✅ Criado |
| `infra/terraform/scheduler.tf` — `build_radar_index` | ✅ Modificado |

---

### Alert SLA stamp

| Arquivo | Status |
|---------|--------|
| `app/agents/alert_agent.py` — `_latency_minutes()` | ✅ Modificado |

---

### Config & Infra

| Arquivo | Adição |
|---------|--------|
| `app/core/config.py` | vertex_index_id, vertex_index_endpoint_id, rag_* settings |
| `infra/terraform/vertex.tf` | Vertex AI Index + Endpoint (STREAM_UPDATE, 768d) |
| `infra/terraform/scheduler.tf` | `predict_drops` (weekly Mon 02h UTC), `build_radar_index` (monthly 1st 03h UTC) |

---

### Frontend — property detail

`frontend/app/imoveis/[id]/page.tsx` atualizado com:
- `<PriceDropForecast propertyId={id} />` — barras de probabilidade 30/60/90d
- `<AskEdital propertyId={id} />` — formulário RAG com citações em blockquote

---

## Decisões notáveis

1. **JSONB → JSON**: `prediction.py` migrado de `JSONB` para `JSON` (SQLAlchemy
   cross-compatible) para passar nos testes SQLite sem alterar o comportamento em
   Postgres.

2. **Lazy imports Vertex AI**: todos os imports `vertexai`, `google.cloud.aiplatform`
   estão dentro de funções — o SDK não é necessário no ambiente de testes.

3. **`_format_answer` anti-hallucination**: se `raw_cits` estava não-vazio mas todas
   as citações foram descartadas (`all_citations_stripped=True`), `not_found=True` é
   forçado independentemente do campo `answer`.
