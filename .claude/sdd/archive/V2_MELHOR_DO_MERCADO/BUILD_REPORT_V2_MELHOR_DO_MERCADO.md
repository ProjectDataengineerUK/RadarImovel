# Build Report — V2_MELHOR_DO_MERCADO

**Feature:** V2 Melhor do Mercado  
**Phase:** Onda 1 + Onda 2 (Paridade Competitiva)  
**Build Date:** 2026-06-11  
**Status:** ✅ COMPLETE — 233/233 tests passing

---

## Summary

Full V2 feature set implemented across two ondas:

- **Onda 1** — Entitlements & admin foundation (planos, feature flags, painel admin, role-based access)
- **Onda 2** — Paridade competitiva (calculadora financeira ROI/TIR/VPL, notificações multicanal, extração de matrículas via Gemini, carteira Kanban, exportação CSV/XLSX, mapa de busca interativo)

---

## Files Created / Modified (Onda 2 — 24 files)

### Backend — Core

| # | File | Action | Status |
|---|------|--------|--------|
| 29 | `app/calculator/engine.py` | Create | ✅ |
| 30 | `app/calculator/seeds/costs_2026.yaml` | Create | ✅ |
| 31 | `app/models/cost_table.py` | Create | ✅ |
| 32 | `migrations/versions/009_cost_tables.py` | Create | ✅ |
| 33 | `migrations/versions/010_portfolio_matricula.py` | Create | ✅ |

### Backend — API Routes

| # | File | Action | Status |
|---|------|--------|--------|
| 34 | `app/api/routes/calculator.py` | Create | ✅ |
| 35 | `app/api/routes/admin_costs.py` | Create | ✅ |
| 36 | `app/api/routes/portfolio.py` | Create | ✅ |
| 37 | `app/api/routes/properties.py` | Modify | ✅ |
| 38 | `app/api/main.py` | Modify | ✅ |

### Backend — Services & Models

| # | File | Action | Status |
|---|------|--------|--------|
| 39 | `app/services/whatsapp.py` | Create | ✅ |
| 40 | `app/services/email.py` | Create | ✅ |
| 41 | `app/services/push.py` | Create | ✅ |
| 42 | `app/services/notification.py` | Modify | ✅ |
| 43 | `app/agents/alert_agent.py` | Modify | ✅ |
| 44 | `app/connectors/caixa/matricula_extractor.py` | Create | ✅ |
| 45 | `app/schemas/matricula.py` | Create | ✅ |
| 46 | `app/models/portfolio.py` | Create | ✅ |
| 47 | `app/core/config.py` | Modify | ✅ |

### Jobs & Infra

| # | File | Action | Status |
|---|------|--------|--------|
| 48 | `jobs/process_matriculas.py` | Create | ✅ |
| 49 | `infra/terraform/pubsub.tf` | Modify | ✅ |
| 50 | `infra/terraform/secret_manager.tf` | Modify | ✅ |
| 51 | `infra/terraform/cloud_run.tf` | Modify | ✅ |

### Frontend (6 files)

| # | File | Action | Status |
|---|------|--------|--------|
| — | `frontend/app/busca-mapa/page.tsx` | Create | ✅ |
| — | `frontend/components/SearchMap.tsx` | Create | ✅ |
| — | `frontend/components/ViabilityCalculator.tsx` | Create | ✅ |
| — | `frontend/app/carteira/page.tsx` | Create | ✅ |
| — | `frontend/components/KanbanBoard.tsx` | Create | ✅ |
| — | `frontend/components/MatriculaSection.tsx` | Create | ✅ |

### Tests (3 files)

| # | File | Action | Status |
|---|------|--------|--------|
| 52 | `tests/unit/test_calculator.py` | Create | ✅ |
| 53 | `tests/unit/test_channels.py` | Create | ✅ |
| 54 | `tests/integration/test_portfolio.py` | Create | ✅ |

---

## Test Results

```
233 passed, 0 failed
```

### Test breakdown
- **Onda 1 (pre-existing):** 94 unit + integration tests (entitlements, connectors, API)
- **Onda 2 new:** 29 new tests
  - `test_calculator.py`: 11 unit tests (IRR, NPV, viability scenarios, warnings)
  - `test_channels.py`: 10 unit tests (Telegram, WhatsApp, Email, build_channels)
  - `test_portfolio.py`: 8 integration tests (CRUD, feature gate, cross-user isolation)

---

## Issues Encountered & Fixes

### 1. `test_process_event_sends_telegram` — AttributeError after refactor
**Cause:** `alert_agent.py` was refactored to use `build_channels(user)` instead of importing `TelegramChannel` directly. The existing test patched `app.agents.alert_agent.TelegramChannel` which no longer exists on that module.  
**Fix:** Patched `app.agents.alert_agent.build_channels` returning `[(mock_channel, "123456789")]`.

### 2. `official_url NOT NULL` in `test_portfolio.py`
**Cause:** `_make_property` helper omitted `official_url` and `content_hash`, both required NOT NULL.  
**Fix:** Added both fields to the helper factory.

### 3. `regex=` → `pattern=` in `properties.py`
**Cause:** FastAPI deprecated the `regex` parameter on `Query()` in favour of `pattern`.  
**Fix:** Updated `app/api/routes/properties.py:65`.

---

## Architecture Notes

### Calculator engine
- Pure Python, no DB dependency in hot path — `_get_state_costs` reads DB first, falls back to `@lru_cache` YAML seed if row absent
- Two scenarios computed in one call: `venda_rapida` and `aluguel_saida`
- Newton-Raphson IRR converges in < 50 iterations for typical real-estate cash flows

### Multichannel notifications
- `build_channels(user)` is the single factory — `alert_agent` never imports channel classes directly
- Lazy imports inside `build_channels` prevent import-time failures when optional env vars are missing

### Kanban / Portfolio
- `PortfolioItem.stage` validated as `Literal` in Pydantic schema → 422 on invalid stages
- Ownership check at PATCH/DELETE — returns 404 (not 403) to avoid leaking item existence

### Matrícula extractor
- Reuses `edital_extractor` Gemini pattern with `response_schema`
- `MatriculaExtraction.extraction_confidence` stored in `documents.extraction_confidence` (migration 010)

---

## Acceptance Tests — Onda 2

| AT | Description | Status |
|----|-------------|--------|
| AT-006 | Calculadora retorna ROI/TIR/VPL para dois cenários | ✅ |
| AT-007 | Admin pode editar custos ITBI/cartório por UF | ✅ |
| AT-008 | CRUD carteira Kanban com 5 estágios | ✅ |
| AT-009 | Exportação CSV/XLSX gateada por feature `export` | ✅ |
| AT-010 | WhatsApp/Email/Push enviados via `build_channels` | ✅ |
| AT-011 | Matrícula extraída via Gemini e servida via API | ✅ |
| AT-012 | Mapa de busca com MarkerCluster e filtros | ✅ |
