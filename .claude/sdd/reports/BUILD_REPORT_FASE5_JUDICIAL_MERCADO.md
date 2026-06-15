# BUILD REPORT — Fase 5: Judicial + Mercado

**Data:** 2026-06-15  
**Branch:** main  
**Status:** ✅ COMPLETO  
**Testes:** 272 passando / 0 falhando

---

## Resumo Executivo

Fase 5 shipped: plataforma expandida de 7 bancos + 5 leiloeiros para **16 fontes** (bancos + leiloeiros + fontes judiciais). Adicionados detectores automáticos de 2ª Praça, comparação com mercado FipeZap, calculadora de ROI e alertas especializados.

---

## Arquivos Criados/Modificados

### Conectores Novos (4)

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `app/connectors/lance_certo/collector.py` | ✅ | Scraper Lance Certo com fallback Playwright |
| `app/connectors/lance_certo/parser.py` | ✅ | Parser HTML multi-seletor |
| `app/connectors/lance_certo/normalizer.py` | ✅ | Normaliza p/ schema Property |
| `app/connectors/superleiloes/collector.py` | ✅ | Scraper JSON+HTML Super Leilões |
| `app/connectors/superleiloes/parser.py` | ✅ | Parser JSON (API) + HTML (fallback) |
| `app/connectors/superleiloes/normalizer.py` | ✅ | Normaliza p/ schema Property |
| `app/connectors/tjsp/__init__.py` | ✅ | Export TJSPConnector |
| `app/connectors/tjsp/collector.py` | ✅ | Usa DataJud search_hastas_tribunal |
| `app/connectors/tjsp/parser.py` | ✅ | Parser hits DataJud |
| `app/connectors/tjsp/normalizer.py` | ✅ | Normaliza processos judiciais |

### Agentes e Detectores

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `app/agents/second_auction_detector.py` | ✅ (prev) | Detecta queda ≥40% → 2ª Praça |
| `app/agents/change_detector.py` | ✅ MOD | Hook p/ SecondAuctionDetector em `minimum_value` |
| `app/agents/alert_agent.py` | ✅ MOD | Handler `segunda_praca` event_type |

### Serviços

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `app/services/fipezap.py` | ✅ (prev) | Cliente FipeZap + BCB Selic |
| `app/services/telegram.py` | ✅ MOD | `format_segunda_praca_alert()` |
| `app/risk/sources/datajud.py` | ✅ MOD | `TRIBUNAL_CODES`, `HASTA_CLASS_CODES`, `search_hastas_tribunal()` |

### Calculadora

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `app/calculator/roi.py` | ✅ (prev, fixed) | Float-to-Decimal conversão corrigida |
| `app/calculator/__init__.py` | ✅ (prev) | Exports ROIInput, ROIResult, calculate_roi |

### Registry

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `app/connectors/__init__.py` | ✅ MOD | +4 fontes: lance_certo, superleiloes, judicial, tjsp |

### Migration

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `migrations/versions/014_fase5_judicial.py` | ✅ (prev) | market_prices table + 5 colunas Property |

### API

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `app/api/routes/market.py` | ✅ | `GET /market/prices` + `POST /market/properties/{id}/roi` |
| `app/api/main.py` | ✅ MOD | `app.include_router(market.router)` |

### Jobs

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `jobs/collect_judicial.py` | ✅ | Job parametrizado por `TRIBUNAL` env var |
| `jobs/collect_market_prices.py` | ✅ | Job mensal FipeZap com upsert |

### Terraform

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `infra/terraform/cloud_run.tf` | ✅ MOD | +2 jobs: radar-collect-judicial, radar-collect-market-prices |
| `infra/terraform/scheduler.tf` | ✅ MOD | +3 schedulers judiciais (TRT2/TRT15/TJSP) + 1 mensal mercado |

### Frontend

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `frontend/components/SecondAuctionBadge.tsx` | ✅ | Badge 2ª Praça vermelho |
| `frontend/components/MarketComparisonBadge.tsx` | ✅ | Badge comparação FipeZap |
| `frontend/components/ROICalculator.tsx` | ✅ | Calculadora interativa ROI/yield/payback/CDI |
| `frontend/app/imoveis/[id]/roi/page.tsx` | ✅ | Página dedicada ROI por imóvel |

### Testes (29 novos)

| Arquivo | Testes | Status |
|---------|--------|--------|
| `tests/unit/connectors/test_judicial_parser.py` | 6 | ✅ |
| `tests/unit/connectors/test_lance_certo_parser.py` | 4 | ✅ |
| `tests/unit/connectors/test_superleiloes_parser.py` | 5 | ✅ |
| `tests/unit/agents/test_second_auction_detector.py` | 5 | ✅ |
| `tests/unit/calculator/test_roi.py` | 6 | ✅ |
| `tests/unit/services/test_fipezap.py` | 4 | ✅ |
| `tests/unit/connectors/test_registry.py` | ATUALIZADO | ✅ 16 sources |

---

## Bugs Corrigidos durante Build

| Bug | Arquivo | Fix |
|-----|---------|-----|
| `Decimal * float` TypeError | `app/calculator/roi.py` | Wrapping explícito `Decimal(str(...))` em todos os floats antes de operações |
| Selic em % vs decimal | `tests/unit/calculator/test_roi.py` | Corrigido para passar `0.105` não `10.5` |
| Mock SQLAlchemy errado | `tests/unit/services/test_fipezap.py` | `session.execute().fetchone()` ao invés de `session.query().filter().first()` |
| Registry size mismatch | `tests/unit/connectors/test_registry.py` | Atualizado de 12 para 16 sources + adicionados imports |

---

## Arquitetura de Eventos

```
Property.minimum_value cai ≥40%
→ change_detector.py detecta
→ SecondAuctionDetector.detect()
→ Property.auction_stage = "segunda_praca"
→ Pub/Sub event_type="segunda_praca"
→ alert_agent.process_segunda_praca_event()
→ format_segunda_praca_alert() → Telegram
```

---

## SOURCE_REGISTRY atualizado (16 fontes)

**Bancos (7):** caixa, bb, brb, bnb, basa, banrisul, banestes  
**Leiloeiros (5):** zuk, mega, sodre, fidalgo, frazao  
**Novos (4):** lance_certo, superleiloes, judicial, tjsp

---

## Próximos passos (Fase 6)

- Adicionar TRF3, TJRJ, TJMG ao scheduler quando validado
- Integrar `discount_vs_market_pct` na API properties e PropertyCard
- WhatsApp/SendGrid como canal adicional de alertas de 2ª Praça
- Dashboard de comparação mercado na página `/radar-index`
