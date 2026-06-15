# DEFINE: Fase 5 — Leilões Judiciais + Inteligência de Mercado

> Cobertura de tribunais (TRT, TRF, TJs), novos leiloeiros judiciais (Lance Certo, Superleilões), detector de 2ª praça, calculadora ROI, preço/m² vs. mercado (FipeZap) e Radar Index granular por município.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FASE5_JUDICIAL_MERCADO |
| **Date** | 2026-06-14 |
| **Author** | define-agent |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |
| **Source** | BRAINSTORM_FASE5_JUDICIAL_MERCADO.md |

---

## Problem Statement

O Radar Imóvel cobre 7 bancos públicos e 5 leiloeiros extrajudiciais. O segmento de **leilões judiciais** — hastas públicas oriundas de TRTs (trabalhista), TRFs (federal) e TJs estaduais — oferece os maiores descontos do mercado (40–70%) e nenhum concorrente os monitora sistematicamente. Adicionalmente, a plataforma não oferece análise de retorno financeiro do investimento nem comparativo automático com preços de mercado, funcionalidades que converteriam usuários em assinantes pagantes. A Fase 5 fecha essas duas lacunas críticas.

---

## Target Users

| User | Pain Point Endereçado |
|------|-----------------------|
| Investidor avançado | Quer hastas judiciais com maiores descontos sem monitorar 24+ tribunais manualmente |
| Investidor iniciante | Quer saber se o imóvel é um bom negócio vs. outras aplicações financeiras |
| Corretor especializado | Quer relatório profissional de due diligence para apresentar a clientes |
| Investidor em SP | Quer imóveis do TJSP que seu leiloeiro favorito (Fidalgo/Mega) já opera |

---

## Goals

### MUST (P0)

| ID | Requisito |
|----|-----------|
| RF-J-01 | O sistema detecta automaticamente quando um imóvel vai a **2ª praça** (queda ≥40% no valor mínimo, mesmo `external_code`) e gera alerta P0 para watchlists correspondentes |
| RF-J-02 | O `JudicialConnector` consulta o DataJud API filtrando por tribunal (TRT-1 a TRT-24, TRF-1 a TRF-6) e classe processual (hasta pública, arrematação, penhora ativa) |
| RF-J-03 | O `TJSPConnector` implementa coleta de hastas do TJSP via DataJud (filtrando tribunal `TJSP`) e resolve o leiloeiro designado quando disponível |
| RF-J-04 | Imóveis judiciais coletados passam pelo mesmo pipeline de normalização, score e Pub/Sub `property-events` que os imóveis de bancos |
| RF-J-05 | O campo `source_type` (enum: `bank`, `auctioneer`, `judicial`) diferencia imóveis judiciais no painel e nos alertas |

### MUST (P1)

| ID | Requisito |
|----|-----------|
| RF-M-01 | Job mensal `collect_market_prices` baixa dados FipeZap e popula tabela `market_prices` com preço/m² médio por cidade e tipo de imóvel |
| RF-M-02 | O card do imóvel exibe "R$ X/m² (leilão) vs. R$ Y/m² (mercado em [cidade]) = Z% abaixo" quando o dado de mercado estiver disponível |
| RF-M-03 | O endpoint `/properties/{id}` retorna o campo `market_comparison` com `price_per_sqm_auction`, `price_per_sqm_market`, `discount_vs_market_pct` |
| RF-M-04 | A calculadora ROI é acessível no frontend via `/imoveis/{id}/roi` e aceita inputs: intenção (revenda/aluguel/moradia), custo de reforma (R$/m²), horizonte (meses) |
| RF-M-05 | A calculadora retorna: ROI (%), yield anual (%), payback (meses), comparativo com CDB 100% CDI |
| RF-TRT-01 | O sistema coleta hastas públicas de pelo menos 5 TRTs prioritários: TRT-2 (SP), TRT-3 (MG), TRT-4 (RS), TRT-15 (Campinas), TRT-1 (RJ) |
| RF-TRF-01 | O sistema coleta hastas públicas do TRF-3 (SP/MS) e TRF-1 (maiores estados) via DataJud |
| RF-LC-01 | O `LanceCertoConnector` implementa coleta do portal Lance Certo com foco em imóveis judiciais |
| RF-SL-01 | O `SuperleiloesConnector` implementa coleta do portal Superleilões com filtro por categoria imóvel |

### SHOULD (P2)

| ID | Requisito |
|----|-----------|
| RF-RI-01 | O Radar Index quebra por **município** além de UF, exibindo top 20 municípios com maior deságio médio |
| RF-RI-02 | O Radar Index exibe tendência (seta + percentual): deságio subindo ou descendo vs. mês anterior |
| RF-RI-03 | O mapa da página `/mapa` suporta camada "oportunidade" (heatmap de deságio) além da camada "risco" existente |
| RF-SPU-01 | O `SPUConnector` coleta alienações publicadas no portal gov.br/spu |
| RF-DD-01 | O relatório de due diligence PDF (`/properties/{id}/report`) inclui: score, risco multidimensional, resumo do edital (IA), preço/m² vs. mercado, processos vinculados (DataJud) |
| RF-DD-02 | O relatório PDF suporta logo customizável (white-label) via configuração de usuário premium |

### COULD (P3)

| ID | Requisito |
|----|-----------|
| RF-WD-01 | Para imóveis favoritados com processo judicial vinculado, o sistema monitora diariamente o DataJud e alerta em caso de: nova penhora, recurso suspensivo, adjudicação |
| RF-PWA-01 | O frontend é servido como PWA com service worker e suporte a Web Push Notifications |
| RF-PGFN-01 | O `PGFNConnector` coleta leilões de bens penhorados da dívida ativa federal |

---

## Requisitos Funcionais Detalhados

### 2ª Praça Detector

| ID | Requisito |
|----|-----------|
| RF-2P-01 | O `SecondAuctionDetector` é invocado pelo `change_detector` sempre que `minimum_value` de um imóvel cai mais de 40% em relação ao valor anterior |
| RF-2P-02 | Ao detectar 2ª praça, o agente atualiza o campo `auction_stage` = `segunda_praca` na tabela `properties` |
| RF-2P-03 | O agente publica evento no tópico Pub/Sub `property-events` com `event_type` = `segunda_praca` e `priority` = `HIGH` |
| RF-2P-04 | O `alert_agent` trata eventos `segunda_praca` com template de alerta diferenciado: "ALERTA 2ª Praça: [imóvel] — valor caiu de R$X para R$Y" |
| RF-2P-05 | O card do imóvel no frontend exibe badge "2ª Praça" em destaque vermelho quando `auction_stage = segunda_praca` |
| RF-2P-06 | O filtro de busca permite selecionar apenas imóveis em 2ª praça |

### JudicialConnector (DataJud)

| ID | Requisito |
|----|-----------|
| RF-J-06 | `JudicialConnector.discover_sources()` retorna uma lista de `(tribunal_code, page)` para iterar o DataJud |
| RF-J-07 | `JudicialConnector.fetch_raw(tribunal_code, page)` chama `DataJudClient.search_hasta()` com filtros de tribunal e classe e retorna JSON serializado |
| RF-J-08 | `JudicialConnector.parse(raw_bytes)` transforma cada hit do DataJud em `RawProperty` com campos: `external_code` (número do processo), `title` (resumo do bem), `city`, `state`, `minimum_value` (valor de avaliação do laudo), `bank_code` = `judicial`, `source_url` (link para o processo público no DataJud), `auction_date` |
| RF-J-09 | Quando o hit do DataJud referencia um leiloeiro específico, `JudicialConnector` resolve e armazena `auctioneer_name` e `auctioneer_url` |
| RF-J-10 | `JudicialNormalizer.normalize()` mapeia o `RawProperty` judicial para o schema `Property` com `source_type = judicial` |
| RF-J-11 | O job `collect_judicial.py` aceita env vars: `TRIBUNAL` (ex: `TRT2`, `TRF3`, `TJSP`), `DAYS_BACK` (janela de busca, default 30) |
| RF-J-12 | Se o DataJud retornar erro 429 (rate limit), o job implementa backoff exponencial (2s, 4s, 8s, max 64s) antes de retentar |
| RF-J-13 | Imóveis judiciais sem endereço completo (comum nos dados do DataJud) passam pelo geocoding enriquecido usando `city` + `state` + palavras-chave do título |

### FipeZap — Preço de Mercado

| ID | Requisito |
|----|-----------|
| RF-FZ-01 | O job `collect_market_prices.py` executa mensalmente via Cloud Scheduler |
| RF-FZ-02 | O job baixa o índice FipeZap para venda e aluguel, por cidade e por tipo (residencial, apartamento, casa) |
| RF-FZ-03 | Os dados são armazenados na tabela `market_prices(id, city, uf, property_type, price_per_sqm_sale, price_per_sqm_rent, reference_month, source)` |
| RF-FZ-04 | O endpoint `/market-prices?city=São Paulo&property_type=apartamento` retorna o preço de mercado mais recente |
| RF-FZ-05 | A comparação de mercado é calculada no momento do fetch do imóvel (não em batch) usando `city` + `property_type` para lookup na tabela `market_prices` |
| RF-FZ-06 | Se não houver dado FipeZap para a cidade, o sistema usa dados do município mais próximo com dados disponíveis (dentro do mesmo estado) |

### Calculadora ROI

| ID | Requisito |
|----|-----------|
| RF-ROI-01 | A calculadora é um endpoint `POST /properties/{id}/roi` que aceita `{ intention, reform_cost_per_sqm, horizon_months }` |
| RF-ROI-02 | Para intenção `revenda`: `roi = (market_value - lance - reform_cost - transaction_costs) / (lance + reform_cost)` onde `transaction_costs` = 4% (ITBI + registro) |
| RF-ROI-03 | Para intenção `aluguel`: `yield_annual = (monthly_rent * 12) / (lance + reform_cost)` onde `monthly_rent = price_per_sqm_rent * area_sqm` |
| RF-ROI-04 | O payback é calculado como `(lance + reform_cost) / (monthly_rent - condominium - iptu)` em meses |
| RF-ROI-05 | O comparativo com CDB usa a taxa Selic atual (buscada via API Bacen `api.bcb.gov.br` — endpoint já implementado via `app/risk/sources/transparencia.py`) |
| RF-ROI-06 | A resposta inclui: `roi_pct`, `yield_annual_pct`, `payback_months`, `cdi_equivalent_pct`, `net_gain_vs_cdi` |
| RF-ROI-07 | O frontend exibe a calculadora como modal na página de detalhe do imóvel com sliders para os inputs |

### LanceCertoConnector

| ID | Requisito |
|----|-----------|
| RF-LC-02 | `LanceCertoConnector.discover_sources()` retorna URLs paginadas de listagem de imóveis no Lance Certo |
| RF-LC-03 | `LanceCertoConnector.fetch_raw()` usa `httpx` com headers de browser; fallback Playwright se receber 403 |
| RF-LC-04 | `LanceCertoParser.parse()` extrai: lote, tipo, endereço, cidade/UF, valor de avaliação, lance mínimo, data do leilão, link do edital, número do processo judicial (quando disponível) |
| RF-LC-05 | `LanceCertoNormalizer.normalize()` mapeia para schema `Property` com `bank_code = "lance_certo"`, `source_type = judicial` quando número de processo presente |

### SuperleiloesConnector

| ID | Requisito |
|----|-----------|
| RF-SL-02 | `SuperleiloesConnector.discover_sources()` retorna URLs filtrando por categoria "imóveis" no portal Superleilões |
| RF-SL-03 | `SuperleiloesConnector.fetch_raw()` usa Playwright (site React/SPA) aguardando listagem de lotes renderizar |
| RF-SL-04 | `SuperleiloesParser.parse()` extrai: lote, título, cidade/UF, valor de avaliação, lance mínimo, data, modalidade (judicial/extrajudicial), link |
| RF-SL-05 | `SuperleiloesNormalizer.normalize()` mapeia para schema `Property` com `bank_code = "superleiloes"` |

### Radar Index Granular

| ID | Requisito |
|----|-----------|
| RF-RI-04 | O endpoint `/radar-index?granularity=city` agrega deságio médio por município (não apenas UF) |
| RF-RI-05 | O endpoint `/radar-index?granularity=state` mantém o comportamento atual (compatibilidade) |
| RF-RI-06 | A query SQL de aggregation usa `ST_AsText(geocoded_point)` para agrupar por cidade quando `city` não está preenchido |
| RF-RI-07 | O campo `trend` na resposta indica variação do deságio vs. mês anterior: `up`, `down`, `stable` |
| RF-RI-08 | O endpoint `/radar-index/hotspots` retorna os 10 municípios com maior deságio médio no período atual |

---

## Schema Changes

### Nova tabela: `market_prices`

```sql
CREATE TABLE market_prices (
    id                   SERIAL PRIMARY KEY,
    city                 VARCHAR(100) NOT NULL,
    uf                   CHAR(2) NOT NULL,
    property_type        VARCHAR(50),          -- 'apartamento', 'casa', 'geral'
    price_per_sqm_sale   NUMERIC(12,2),
    price_per_sqm_rent   NUMERIC(12,2),
    reference_month      DATE NOT NULL,
    source               VARCHAR(50) DEFAULT 'fipezap',
    created_at           TIMESTAMP DEFAULT now(),
    UNIQUE (city, uf, property_type, reference_month, source)
);
```

### Alter: `properties`

```sql
ALTER TABLE properties
    ADD COLUMN source_type   VARCHAR(20) DEFAULT 'bank',   -- 'bank', 'auctioneer', 'judicial'
    ADD COLUMN auction_stage VARCHAR(30),                   -- NULL, 'primeira_praca', 'segunda_praca'
    ADD COLUMN auctioneer_name VARCHAR(100),                -- leiloeiro designado (judicial)
    ADD COLUMN process_number VARCHAR(50),                  -- número do processo CNJ (judicial)
    ADD COLUMN market_price_per_sqm NUMERIC(12,2),         -- snapshot do FipeZap no momento da coleta
    ADD COLUMN discount_vs_market_pct NUMERIC(5,2);        -- calculado automaticamente
```

### Alter: `banks` (adicionar registros para fontes judiciais)

```sql
INSERT INTO banks (code, name, active) VALUES
    ('judicial_trt',    'Judicial — TRT',  true),
    ('judicial_trf',    'Judicial — TRF',  true),
    ('judicial_tjsp',   'Judicial — TJSP', true),
    ('judicial_tjrj',   'Judicial — TJRJ', false),
    ('lance_certo',     'Lance Certo',     true),
    ('superleiloes',    'Superleilões',    true),
    ('spu',             'SPU',             false);  -- fase posterior
```

---

## Non-goals (explicitamente fora do escopo da Fase 5)

- Integração com cartórios para consulta de matrícula (Fase 6)
- OCR avançado para editais escaneados via Document AI (já planejado em fases futuras)
- WhatsApp como canal de alerta (Fase 6)
- PWA completo com push notifications (P3, pode ser Fase 6)
- Prefeituras / IPTU em débito por município (complexidade: 5.570 municípios)
- PGFN / Receita Federal (P3 — data incerta)

---

## Acceptance Criteria

| Critério | Como verificar |
|---------|----------------|
| Detector 2ª praça funciona | Simular queda de 50% no `minimum_value` de um imóvel de teste → evento `segunda_praca` publicado no Pub/Sub |
| JudicialConnector coleta do DataJud | `collect_judicial.py TRIBUNAL=TRT2` popula ≥1 imóvel na tabela `properties` com `source_type = judicial` |
| FipeZap integrado | `GET /market-prices?city=São Paulo` retorna dado de mercado com `reference_month` ≤ 30 dias |
| Calculadora ROI | `POST /properties/{id}/roi` retorna JSON com `roi_pct`, `yield_annual_pct`, `payback_months` |
| Lance Certo coleta | `collect_bank.py BANK=lance_certo` popula ≥1 imóvel |
| Superleilões coleta | `collect_bank.py BANK=superleiloes` popula ≥1 imóvel |
| Radar Index por cidade | `GET /radar-index?granularity=city` retorna agregações por município com campo `trend` |
| Badge 2ª praça no frontend | Card do imóvel exibe badge vermelho "2ª Praça" quando `auction_stage = segunda_praca` |
| Comparativo de mercado no card | Imóvel com área e cidade conhecidos exibe "X% abaixo do mercado" se dado FipeZap disponível |

---

## Dependências

| Dependência | Tipo | Status |
|-------------|------|--------|
| DataJud API CNJ | Externa (API pública) | ✅ cliente já implementado |
| FipeZap | Externa (scraping/API) | Validar formato dos dados |
| Bacen API (taxa Selic) | Externa (API pública) | ✅ `transparencia.py` já acessa BCB |
| Lance Certo | Externa (scraping) | A validar (httpx ou Playwright?) |
| Superleilões | Externa (scraping) | A validar (React SPA = Playwright) |
| `change_detector` | Interna | ✅ existe |
| `property_changes` tabela | Interna | ✅ existe com `old_value`/`new_value` |
| `pdf_report.py` | Interna | ✅ existe, expandir |
| PostGIS + geocoding | Interna | ✅ já em uso |
