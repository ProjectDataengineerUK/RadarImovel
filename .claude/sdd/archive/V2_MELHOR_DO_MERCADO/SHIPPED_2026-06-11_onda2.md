# SHIPPED — V2_MELHOR_DO_MERCADO (Onda 2: Paridade Competitiva)

**Status:** ✅ Shipped  
**Ship Date:** 2026-06-11  
**Phase:** 4 (Archive)  
**Tests:** 233/233 passing (0 regressions)

---

## Summary

Onda 2 entrega a camada de paridade competitiva do Radar Imóvel — as features que colocam a plataforma no mesmo nível das ferramentas premium do mercado.

**O que foi entregue:**

- **Calculadora financeira** (`app/calculator/engine.py`) — ROI, TIR (Newton-Raphson), VPL, payback, rendimento bruto anual. Dois cenários por imóvel: `venda_rapida` e `aluguel_saida`. Custos de aquisição (ITBI/cartório/registro) por UF via DB com fallback em YAML seed.
- **CostTable** — modelo editável por admin, rota `PUT /admin/costs/{state}` com auditoria, `lru_cache` limpo após update.
- **Notificações multicanal** — `WhatsAppChannel` (Meta API), `EmailChannel` (SendGrid), `PushChannel` (FCM HTTP v1). `build_channels(user)` é o único ponto de instanciação — `alert_agent` nunca importa canais diretamente.
- **Extrator de matrícula** (`matricula_extractor.py`) — Gemini com `response_schema` estruturado (`MatriculaExtraction`), mesmo padrão do `edital_extractor`. Job `process_matriculas` consome `matricula-events`.
- **Carteira Kanban** — `PortfolioItem` (5 estágios), CRUD com ownership check, gateado por feature `portfolio`.
- **Exportação CSV/XLSX** — streaming response, gateado por feature `export`.
- **Mapa de busca** — `SearchMap.tsx` com Leaflet + MarkerCluster, color-coded por score de oportunidade, filtros de estado/cidade/preço/desconto.

---

## Timeline

| Marco | Data |
|-------|------|
| Onda 1 shipped | 2026-06-11 |
| Build Onda 2 iniciado | 2026-06-11 |
| Todos os testes passando | 2026-06-11 |
| Ship Onda 2 | 2026-06-11 |

---

## Métricas

| Métrica | Valor |
|---------|-------|
| Arquivos criados/modificados (Onda 2) | 24 |
| Novos testes | 29 (11 unit + 10 unit + 8 integration) |
| Testes totais na suíte | 233 |
| Regressões | 0 |
| Ondas completas (V2 total) | 2/4 |

---

## Lições Aprendidas

### ✅ O que funcionou bem

**`build_channels` como única fábrica de canais**
Centralizar a instanciação de `NotificationChannel` em uma função única elimina o problema de "o teste precisa saber qual canal foi usado". Basta mockar `build_channels` retornando `[(mock_channel, "dest")]` — sem precisar saber se é Telegram, WhatsApp ou outro.

**YAML seed com `@lru_cache(maxsize=1)`**
O fallback de custos em YAML carregado com `lru_cache` é transparente: funciona em testes (SQLite sem tabela `cost_tables`) e em produção sem overhead. A limpeza do cache com `_load_seed_costs.cache_clear()` após um PUT admin garante que updates sejam refletidos imediatamente.

**`ViabilityResult` como dataclass puro**
Não herdar de `BaseModel` no `engine.py` permite chamar `calculate_viability` sem contexto FastAPI, SQLAlchemy ou Pydantic — ideal para testes unitários limpos. A conversão para `dict` acontece só no router.

### ⚠️ O que melhorar

**NOT NULL constraints nos helpers de test**
`_make_property()` em `test_portfolio.py` omitiu `official_url` (NOT NULL) e `content_hash`. O padrão correto: helpers de fixtures devem sempre incluir todos os campos NOT NULL. Uma factory function parametrizada (`make_property(db, **overrides)`) reduz esse risco.

**Patch em módulos que reexportam**
`alert_agent.py` reexporta `build_channels` via `from app.services.notification import build_channels`. Isso cria dois nomes para o mesmo objeto. Para que `patch("app.agents.alert_agent.build_channels")` funcione, `alert_agent` precisa importar com `from ... import build_channels` (não `import app.services.notification`). Sempre verificar onde o símbolo vive *no momento do patch*.

**`regex=` → `pattern=` em Query FastAPI**
O parâmetro `regex` foi depreciado no FastAPI 0.100+ em favor de `pattern`. Warnings silenciosos acumulam — idealmente são tratados como erros em CI (`filterwarnings = error::DeprecationWarning` no pytest.ini para warnings do projeto).

---

## Acceptance Tests — Onda 2

| AT | Descrição | Status |
|----|-----------|--------|
| AT-006 | Calculadora retorna ROI/TIR/VPL para dois cenários | ✅ |
| AT-007 | Admin edita custos ITBI/cartório por UF | ✅ |
| AT-008 | CRUD carteira Kanban com 5 estágios | ✅ |
| AT-009 | Exportação CSV/XLSX gateada por feature `export` | ✅ |
| AT-010 | WhatsApp/Email/Push via `build_channels` | ✅ |
| AT-011 | Matrícula extraída via Gemini e servida via API | ✅ |
| AT-012 | Mapa de busca com MarkerCluster e filtros | ✅ |

---

## Artefatos Arquivados

| Arquivo | Descrição |
|---------|-----------|
| `DEFINE_V2_MELHOR_DO_MERCADO.md` | Requisitos completos V2 (Ondas 1–4) |
| `DESIGN_V2_MELHOR_DO_MERCADO.md` | Arquitetura detalhada, manifesto de 52 arquivos |
| `BUILD_REPORT_V2_MELHOR_DO_MERCADO.md` | Relatório de build (Onda 1 + Onda 2, 52 arquivos, 233 testes) |
| `SHIPPED_2026-06-11.md` | Ship da Onda 1 (entitlements + admin) |
| `SHIPPED_2026-06-11_onda2.md` | Este documento |

---

## Próximas Ondas (V2 pendente)

| Onda | Tema | Status |
|------|------|--------|
| Onda 3 | Precificação inteligente (preço/m², comparação de mercado, heatmap) | Pendente |
| Onda 4 | Relatórios e insights (PDF, comparação histórica, projeção) | Pendente |
