# SHIPPED — V2_MELHOR_DO_MERCADO (Onda 3: Máximo de Fontes)

**Status:** ✅ Shipped  
**Ship Date:** 2026-06-12  
**Phase:** 4 (Archive)  
**Tests:** 277/277 passing (0 regressions, 44 novos)

---

## Summary

Onda 3 entrega a camada de multi-fonte do Radar Imóvel — o mesmo imóvel pode agora ser indexado por múltiplas fontes (banco + leiloeiros) com deduplicação inteligente e melhor preço calculado automaticamente.

**O que foi entregue:**

- **SOURCE_REGISTRY** (`app/connectors/__init__.py`) — 12 fontes: 7 bancos + 5 leiloeiros (Zuk, Mega, Sodré, Fidalgo, Frazão). `CONNECTOR_REGISTRY` mantido como alias para backward compat. `get_source()` ao lado de `get_connector()`.
- **Deduplicador v2** (`app/agents/deduplicator.py`) — 2 estágios: (1a) exact match por `(source_id, external_code)` via offer existente; (1b) backward compat por `(bank_id, external_code)`; (2) geohash de proximidade (~100m) + `SequenceMatcher` título ≥ 0.85 → ofertas no mesmo imóvel; 0.70–0.85 → `possible_duplicate_of` para revisão humana. `_upsert_offer` + `_refresh_best_price` garantem 1 oferta ativa por (property, source) e `best_price = MIN(offers)`. Funções legacy mantidas para `collect_bank.py`.
- **`jobs/collect_source.py`** — job genérico por fonte, usa `SOURCE_REGISTRY`. Bloqueia fontes com `tos_compliant=False` a menos que `FORCE_TOS=true` esteja definido. Usa `process_property` v2 (multi-offer).
- **`app/risk/sources/datajud.py`** — `DataJudClient.search_hasta()` para hastas públicas via DataJud CNJ. Complementa `cnj.py` (processos genéricos) com foco em penhora/hasta/arrematação.
- **`GET /properties/{id}/offers`** — endpoint que retorna offers ativas do imóvel ordenadas por preço, com nome da fonte.
- **`admin_dedup`** — fila de revisão de possíveis duplicatas: `GET /admin/dedup` (lista), `POST /admin/dedup/merge` (confirma mesclagem, transfere offers), `DELETE /admin/dedup/{id}/flag` (falso positivo). Auditado.
- **`frontend/app/admin/duplicatas/page.tsx`** — painel visual de duplicatas com modal de mesclagem lado a lado.
- **Seção multi-fontes na ficha do imóvel** (`frontend/app/imoveis/[id]/page.tsx`) — tabela de N fontes com preço, modalidade, data e link quando `offers.length > 1`.
- **Terraform** (`infra/terraform/scheduler.tf`) — schedulers para 5 leiloeiros (2×/dia, 12h + 20h UTC) via `radar-collect-source` job.

---

## Timeline

| Marco | Data |
|-------|------|
| Onda 2 shipped | 2026-06-11 |
| Build Onda 3 iniciado | 2026-06-12 |
| Todos os testes passando | 2026-06-12 |
| Ship Onda 3 | 2026-06-12 |

---

## Métricas

| Métrica | Valor |
|---------|-------|
| Arquivos criados/modificados | 22 |
| Novos testes | 44 (22 unit + 17 unit dedup/v2 + 5 integration) |
| Testes totais na suíte | 277 |
| Regressões | 0 |
| Ondas completas (V2 total) | 3/4 |

---

## Acceptance Tests

| AT | Descrição | Status |
|----|-----------|--------|
| AT-007 | Novo conector leiloeiro → imóveis deduplicados (1 property, N offers) | ✅ |
| AT-011 | Mesmo imóvel Caixa + leiloeiro → 1 registro com 2 fontes, best_price = menor | ✅ |

---

## Lições Aprendidas

**`FORCE_TOS` como gate jurídico**
`tos_compliant=False` no registro da fonte + verificação no job é o lugar certo para esse gate: não exige mudança de código quando o ToS é aprovado, só uma variável de ambiente. Alternativa (feature flag no entitlements) seria mais pesada sem ganho de rastreabilidade.

**Dedup sem PostGIS em SQLite**
Python puro com `round(lat, 3)` (≈111m) + `SequenceMatcher` funciona como proxy aceitável do geohash+trgm em testes. Em produção, PostGIS `ST_DWithin` + `pg_trgm` darão precisão real. A abstração no `_geo_key` torna trivial a substituição.

**`possible_duplicate_of` como sinal, não decisão**
Nunca mesclar automaticamente. A fila no admin com merge manual é a interface certa: o operador vê ambos os registros, confirma ou descarta, e a auditoria registra a ação.

---

## Próxima Onda

| Onda | Tema | Status |
|------|------|--------|
| Onda 4 | Céu azul: curva preditiva de desconto + RAG "pergunte ao edital" + índice público de deságio | Pendente |
