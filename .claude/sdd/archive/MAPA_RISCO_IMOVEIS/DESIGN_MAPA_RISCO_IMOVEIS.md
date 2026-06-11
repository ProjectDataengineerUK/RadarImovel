# DESIGN: Mapa de Risco de Imóveis

> Score multidimensional (0–100) + mapa de calor por região, cruzando 6 bases públicas (CNJ, IBGE, IBAMA/CEMADEN, IPTU/Transparência, IPEA, Receita Federal) para due diligence automatizada.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | MAPA_RISCO_IMOVEIS |
| **Date** | 2026-06-09 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_MAPA_RISCO_IMOVEIS.md](./DEFINE_MAPA_RISCO_IMOVEIS.md) |
| **Status** | Ready for Build |
| **Confidence** | 0.88 — padrão Pub/Sub + Cloud Run Job reutilizado das fases anteriores; spatial joins com PostGIS já habilitado; CNJ Datajud API pública documentada; únicas incógnitas são cobertura real das APIs externas (tratadas via `score_partial`) |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    MAPA DE RISCO — FLUXO COMPLETO                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  collect_bank.py ──► property-events ──► (existente: alert + edital)         │
│                  │                                                            │
│                  └──► risk-events ──► Cloud Run Job                          │
│                             (novo)     calculate_risk.py                     │
│                                              │                               │
│               ┌──────────────────────────────┤                               │
│               │         6 dimensões          │                               │
│               │                              ▼                               │
│  ┌────────────▼──────┐   ┌──────────────────────────────┐                   │
│  │  APIs Externas    │   │   PostGIS / Cloud Storage     │                   │
│  │  CNJ Datajud      │   │   Shapefiles (IBAMA, CEMADEN) │                   │
│  │  IBGE SIDRA       │   │   risk_geodata_cache          │                   │
│  │  IPEA Atlas Viol. │   └──────────────────────────────┘                   │
│  │  Receita CNPJ     │                  │                                    │
│  │  Transp. IPTU     │                  │                                    │
│  └───────────────────┘                  │                                    │
│               │                         │                                    │
│               └────────────┬────────────┘                                    │
│                            ▼                                                  │
│               ┌────────────────────────┐                                     │
│               │  property_risk_scores  │   (PostgreSQL)                      │
│               │  score_total 0-100     │                                     │
│               │  6 dimensões + JSONB   │                                     │
│               └────────┬───────────────┘                                     │
│                        │                                                     │
│            score mudou > 10 pts?                                             │
│                        ▼                                                     │
│               risk-change-events ──► alert_agent.py (ext. existente)        │
│                                                                               │
│  FastAPI                                                                     │
│  GET /properties/{id}/risk ──────────────────────► RiskSection (frontend)   │
│  GET /map/risk-heatmap     ──► GeoJSON municipios ► RiskMap + Leaflet.heat   │
│  GET /properties/{id}/risk/report ──► WeasyPrint ► PDF download             │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Componente | Propósito | Tecnologia |
|------------|-----------|------------|
| `app/risk/calculator.py` | Orquestra as 6 dimensões e computa score final | Python |
| `app/risk/dimensions/` | 6 módulos independentes, um por dimensão | Python |
| `app/risk/sources/` | Clientes para APIs externas (CNJ, IBGE, IBAMA, etc.) | httpx, geopandas |
| `app/risk/schemas.py` | Pydantic: `RiskScore`, `RiskIndicator`, `RiskLevel` | Pydantic v2 |
| `app/risk/pdf_report.py` | HTML→PDF de due diligence | WeasyPrint |
| `app/models/risk.py` | `PropertyRiskScore` + `RiskGeodataCache` SQLAlchemy | SQLAlchemy 2.0 |
| `app/api/routes/risk.py` | Endpoints REST: score, heatmap GeoJSON, PDF | FastAPI |
| `jobs/calculate_risk.py` | Cloud Run Job: consome `risk-events`, calcula score | Python |
| `migrations/versions/006_risk_scores.py` | Tabelas `property_risk_scores` + `risk_geodata_cache` | Alembic |
| Infra Terraform | Pub/Sub `risk-events` + job `radar-calculate-risk` | Terraform |
| `frontend/components/RiskMap.tsx` | Mapa Leaflet + heat layer + toggle de camadas | Leaflet.js |
| `frontend/components/RiskRadarChart.tsx` | Radar chart de 6 dimensões | Recharts |
| `frontend/app/mapa/page.tsx` | Página full-screen do mapa de calor | Next.js |

---

## Data Flow

```text
1. collect_bank.py cria/atualiza Property
   └── publica risk-events: {property_id, lat, lng, city, state, ibge_code,
                              occupancy_detail?, cnpj_at_address?}

2. calculate_risk.py consome risk-events
   a. Dim A — CNJ: GET datajud.cnj.jus.br/api_publica/processo?...
   b. Dim B — Geo: PostGIS ST_Contains(geom, ST_Point(lng, lat))
                   contra shapefiles IBAMA (APP/APA) e CEMADEN
   c. Dim C — IPTU: scraping do portal de transparência do município
   d. Dim D — Ocupação: lê Document.ai_summary (Fase 2) se disponível
   e. Dim E — IBGE: lookup por código IBGE (tabela local, TTL 30 dias)
   f. Dim F — Mercado: lookup Fipe ZAP API (opcional, pode falhar)
   g. Persiste PropertyRiskScore com indicators JSONB
   h. Se |score_novo - score_anterior| > 10: publica risk-change-events

3. alert_agent.py consome risk-change-events (extensão do existente)
   └── verifica favorites com notify_risk_changes=true
   └── envia Telegram com delta de risco

4. API GET /properties/{id}/risk
   └── lê PropertyRiskScore → serializa RiskScoreResponse

5. API GET /map/risk-heatmap
   └── agrega AVG(score_total) GROUP BY ibge_municipality_code
   └── faz join com GeoJSON de municípios (Cloud Storage, TTL 1h)
   └── retorna FeatureCollection com propriedade `risk_avg`

6. API GET /properties/{id}/risk/report
   └── renderiza HTML template → WeasyPrint → StreamingResponse PDF
```

---

## Key Decisions

### Decision 1: Módulo `app/risk/` isolado vs. extensão do `app/agents/`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-09 |

**Context:** `app/agents/score_agent.py` calcula o score de oportunidade (positivo, quanto maior melhor). O risco é uma dimensão ortogonal (negativo, quanto menor melhor) com fontes completamente diferentes e caching próprio.

**Choice:** Novo módulo `app/risk/` com subpacotes `dimensions/` e `sources/`.

**Rationale:** Separar risk de opportunity mantém SOLID — cada módulo tem uma razão para mudar. O `score_agent.py` muda quando os critérios de oportunidade mudam; `risk/calculator.py` muda quando os critérios de risco ou fontes mudam. Misturar os dois criaria acoplamento desnecessário.

**Alternatives Rejected:**
1. Estender `score_agent.py` — um único arquivo com 300+ linhas misturando lógica de oportunidade e risco; difícil de testar isoladamente
2. Subclasse de `BankConnector` — risco não é um conector; não faz sentido semântico

**Consequences:**
- `app/risk/` importa `app/models/` e `app/core/`; não importa `app/agents/` (sem dependência circular)
- `calculate_risk.py` importa `app/risk/calculator.py` exatamente como `process_editais.py` importa `edital_extractor.py`

---

### Decision 2: Job dedicado vs. inline no `collect_bank.py`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-09 |

**Context:** Calcular risco exige 5+ chamadas HTTP externas + spatial joins. O `collect_bank.py` já tem timeout de 3600s e deve permanecer focado em coleta.

**Choice:** `jobs/calculate_risk.py` separado, consumindo `risk-events` via Pub/Sub — mesmo padrão de `process_editais.py`.

**Rationale:** Desacoplamento por Pub/Sub garante que falha na API CNJ não impede a coleta. `score_partial=true` garante que o score calculável é persistido mesmo com fonte indisponível.

**Alternatives Rejected:**
1. Calcular inline no collect — coleta bloquearia por timeout CNJ; retry da coleta recalcularia risco desnecessariamente
2. Cloud Function trigger — timeout máximo insuficiente (1h) para lotes grandes; modelo de Cloud Run Job já dominado pela equipe

---

### Decision 3: Geoespacial — PostGIS spatial join vs. lookup por código IBGE vs. API externa

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-09 |

**Context:** As dimensões B (ambiental) e E (socioeconômico) requerem dados geoespaciais. Dois tipos de operação: (a) verificar se um ponto está dentro de um polígono (APP, CEMADEN), (b) obter atributos de um município (IDH, homicídios).

**Choice:** Estratégia híbrida:
- Tipo (a) — spatial join: shapefiles de APP/APA/CEMADEN carregados em tabelas PostGIS via `risk_geodata_cache`; `ST_Contains(geom, ST_Point(lng, lat))` em query SQL
- Tipo (b) — lookup por código IBGE: tabela `ibge_municipality_stats` populada por job de ingestão bulk mensal; join por `ibge_code` (VARCHAR 7) em O(1)

**Rationale:** PostGIS já está habilitado (infra Fase 1). Lookup por código IBGE é ordens de magnitude mais rápido que spatial join para dados municipais. Shapefiles IBAMA/CEMADEN são estáticos (atualização mensal) — cachear em PostGIS é correto.

**Alternatives Rejected:**
1. Google Maps Geocoding API + Places — custo por request; não cobre dados ambientais/sociais
2. Geopandas em-memória no job — cada execução recarregaria shapefiles de ~50MB; lento e memory-intensive

**Consequences:**
- Novo job de carga: `jobs/load_geodata.py` (executa mensalmente; não faz parte desta fase — shapefiles carregados manualmente na primeira vez)
- `property_risk_scores` depende de `lat/lng` estar preenchido na `Property` (geocoding Fase 1 — já implementado)
- Imóvel sem lat/lng: Dim B calculada com fallback por código IBGE (APP municipal, não pontual)

---

### Decision 4: PDF de due diligence — WeasyPrint vs. ReportLab vs. Puppeteer

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-09 |

**Context:** O relatório de due diligence deve ser exportável como PDF formatado com tabelas, scores coloridos e fontes das informações.

**Choice:** WeasyPrint (`pip install weasyprint`) — renderiza HTML/CSS para PDF server-side.

**Rationale:** HTML+CSS é mais fácil de manter que ReportLab (baixo nível, código verboso). WeasyPrint não exige browser headless (ao contrário de Puppeteer), é Python puro, e funciona no Cloud Run sem dependências de sistema além de `libpango`. O template HTML pode reutilizar os mesmos componentes visuais do frontend (dark theme, cores por faixa de risco).

**Alternatives Rejected:**
1. ReportLab — código verboso; difícil de estilizar; não tem CSS
2. Puppeteer/Playwright headless — adiciona ~300MB à imagem Docker; timeout imprevisível; custo de infra
3. Frontend-side (jsPDF) — não auditável; usuário pode modificar; sem garantia de formato

**Consequences:**
- `weasyprint` adicionado ao extra `api` no `pyproject.toml` (gerado pelo endpoint, não pelo job)
- Imagem Docker da API aumenta ~15MB; aceitável

---

### Decision 5: CNJ Datajud — estratégia de busca

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-09 |

**Context:** A API CNJ Datajud permite busca por número de processo, CPF/CNPJ de parte, ou termo livre. Imóveis de leilão têm CPF/CNPJ do proprietário originais às vezes no edital (extraído pela Fase 2), mas nem sempre.

**Choice:** Dois níveis de busca, do mais ao menos preciso:
1. Se Fase 2 extraiu CPF/CNPJ do proprietário: busca por número do documento filtrada por classes processuais imobiliárias (execução, inventário, usucapião, despejo)
2. Fallback: busca textual pelo endereço normalizado (logradouro + número + município)

**Rationale:** Busca por CPF/CNPJ é precisa e rápida. O fallback por endereço é mais amplo mas cobre imóveis sem edital processado.

**Alternatives Rejected:**
1. Buscar apenas por endereço — falsos positivos (múltiplos imóveis no mesmo logradouro) e falsos negativos (endereços abreviados)
2. Não implementar CNJ agora — a Dimensão A é a de maior peso (30%); sem ela o score perde valor

**Consequences:**
- `app/risk/sources/cnj.py` implementa os dois modos de busca com fallback automático
- `score_partial=true` quando CNJ retorna erro 429 ou timeout

---

### Decision 6: Atualização de scores existentes após recálculo

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-09 |

**Context:** O score de risco deve ser recalculado quando: (a) nova coleta atualiza o imóvel, (b) recálculo manual via admin, (c) job semanal de refresh (scores envelhecem com o tempo).

**Choice:** `property_risk_scores` usa `upsert` por `property_id` (único ativo por imóvel). Mantém histórico apenas em `risk_change_events` Pub/Sub (não persiste histórico de scores no DB para evitar crescimento de tabela).

**Rationale:** Para auditoria, o JSONB `indicators` já contém `date` por indicador. Histórico completo de scores seria outra tabela grande; o DEFINE não exige; logs do Cloud Logging cobrem auditoria operacional.

**Alternatives Rejected:**
1. Tabela de histórico de scores — overhead de storage sem requisito claro
2. Versionar scores com timestamp — útil mas fora do escopo desta fase

---

## File Manifest

### Backend — Python (`app/risk/`)

| # | Arquivo | Ação | Propósito | Deps |
|---|---------|------|-----------|------|
| 1 | `app/risk/__init__.py` | Create | Export público do módulo | — |
| 2 | `app/risk/schemas.py` | Create | Pydantic: `RiskIndicator`, `DimensionScore`, `RiskScoreResult`, `RiskLevel` | — |
| 3 | `app/risk/calculator.py` | Create | Orquestra 6 dimensões; `calculate_risk(property_data, session) → RiskScoreResult` | 2, dims, sources |
| 4 | `app/risk/dimensions/__init__.py` | Create | Export das 6 funções `score_*` | — |
| 5 | `app/risk/dimensions/juridico.py` | Create | Dim A: CNJ — processos, inventário, penhora, usucapião | sources/cnj |
| 6 | `app/risk/dimensions/fundiario.py` | Create | Dim B: PostGIS spatial join APP/APA/CEMADEN/TI + fallback IBGE | sources/geo |
| 7 | `app/risk/dimensions/fiscal.py` | Create | Dim C: IPTU + dívida ativa municipal | sources/transparencia |
| 8 | `app/risk/dimensions/ocupacao.py` | Create | Dim D: dados do edital (Document.ai_summary Fase 2) + CNPJ address | sources/receita |
| 9 | `app/risk/dimensions/socioeconomico.py` | Create | Dim E: IDH, homicídios, vacância, crescimento pop. | sources/ibge, sources/ipea |
| 10 | `app/risk/dimensions/mercado.py` | Create | Dim F: preço/m² vs mercado, oversupply (opcional; falha silenciosa) | sources/fipe |
| 11 | `app/risk/sources/__init__.py` | Create | — | — |
| 12 | `app/risk/sources/cnj.py` | Create | CNJ Datajud REST client (busca por CPF/CNPJ e por endereço) | httpx |
| 13 | `app/risk/sources/ibge.py` | Create | SIDRA API + tabela local `ibge_municipality_stats` (lookup por ibge_code) | httpx, sqlalchemy |
| 14 | `app/risk/sources/ibama.py` | Create | Spatial lookup APP/APA/UC via PostGIS `risk_geodata_layers` | sqlalchemy/GIS |
| 15 | `app/risk/sources/cemaden.py` | Create | Spatial lookup zonas de risco (deslizamento/inundação) via PostGIS | sqlalchemy/GIS |
| 16 | `app/risk/sources/transparencia.py` | Create | Scraping IPTU: estratégia por UF (SP: consulta.prefeitura.sp.gov.br; demais: genérico) | httpx, bs4 |
| 17 | `app/risk/sources/ipea.py` | Create | Atlas da Violência: CSV local `data/atlas_violencia.csv` (carregado em memória) | pandas |
| 18 | `app/risk/sources/receita.py` | Create | Receita Federal CNPJ API: verifica CNPJs ativos no endereço | httpx |
| 19 | `app/risk/sources/fipe.py` | Create | Fipe ZAP ou ZAP Imóveis API: preço/m² por cidade (opcional; retorna `None` se indisponível) | httpx |
| 20 | `app/risk/pdf_report.py` | Create | Gera HTML → WeasyPrint → bytes PDF do relatório de due diligence | weasyprint, jinja2 |
| 21 | `app/risk/templates/due_diligence.html` | Create | Template Jinja2 do PDF: 6 dimensões, indicadores, fontes | — |

### Backend — Models e API

| # | Arquivo | Ação | Propósito | Deps |
|---|---------|------|-----------|------|
| 22 | `app/models/risk.py` | Create | `PropertyRiskScore`, `RiskGeodataLayer`, `IbgeMunicipalityStats` | sqlalchemy |
| 23 | `app/api/routes/risk.py` | Create | 5 endpoints (ver seção API) | risk/calculator, models/risk |
| 24 | `app/api/main.py` | Modify | Registrar `risk_router` | 23 |
| 25 | `app/core/config.py` | Modify | Settings de risco: pesos, thresholds, timeouts de fontes externas | — |

### Database

| # | Arquivo | Ação | Propósito | Deps |
|---|---------|------|-----------|------|
| 26 | `migrations/versions/006_risk_scores.py` | Create | Tabelas `property_risk_scores`, `risk_geodata_layers`, `ibge_municipality_stats` | alembic |

### Jobs

| # | Arquivo | Ação | Propósito | Deps |
|---|---------|------|-----------|------|
| 27 | `jobs/calculate_risk.py` | Create | Entrypoint: consome `risk-events`, chama `calculate_risk()`, persiste, publica `risk-change-events` | risk/calculator |
| 28 | `jobs/collect_bank.py` | Modify | Publica `risk-events` ao criar/atualizar Property (análogo ao `edital-events`) | pubsub |

### Infra Terraform

| # | Arquivo | Ação | Propósito | Deps |
|---|---------|------|-----------|------|
| 29 | `infra/terraform/pubsub.tf` | Modify | Tópicos `risk-events` + `risk-change-events` + DLQs + subscriptions | — |
| 30 | `infra/terraform/cloud_run.tf` | Modify | Job `radar-calculate-risk` (timeout 600s, max_retries 1) | — |
| 31 | `infra/terraform/variables.tf` | Modify | `risk_score_change_threshold`, `risk_job_enabled` | — |

### Frontend Next.js

| # | Arquivo | Ação | Propósito | Deps |
|---|---------|------|-----------|------|
| 32 | `frontend/lib/types.ts` | Modify | Tipos `RiskScore`, `RiskIndicator`, `DimensionScore` | — |
| 33 | `frontend/hooks/useRisk.ts` | Create | React Query: `/properties/{id}/risk` + `/map/risk-heatmap` | types |
| 34 | `frontend/components/RiskScoreBadge.tsx` | Create | Badge: cor por faixa + score 0-100 + label | types |
| 35 | `frontend/components/RiskRadarChart.tsx` | Create | Recharts RadarChart com 6 dimensões normalizadas (0-100) | recharts |
| 36 | `frontend/components/RiskIndicatorList.tsx` | Create | Lista auditável: indicador + valor + fonte + data | types |
| 37 | `frontend/components/RiskMap.tsx` | Create | Leaflet + leaflet.heat + toggle de camadas (APP, CEMADEN, IDH, homicídios) | leaflet |
| 38 | `frontend/components/DueDiligenceButton.tsx` | Create | Botão "Exportar PDF" → download do `/risk/report` | — |
| 39 | `frontend/app/mapa/page.tsx` | Create | Página full-screen: RiskMap + painel lateral de filtros | RiskMap |
| 40 | `frontend/app/imoveis/[id]/page.tsx` | Modify | Adicionar `RiskSection` (RiskScoreBadge + RiskRadarChart + RiskIndicatorList + DueDiligenceButton) | — |
| 41 | `frontend/package.json` | Modify | Adicionar: `leaflet`, `leaflet.heat`, `@types/leaflet`, `recharts` | — |

### Testes

| # | Arquivo | Ação | Propósito | Deps |
|---|---------|------|-----------|------|
| 42 | `tests/unit/risk/test_calculator.py` | Create | Score total, pesos, normalização, score_partial | risk/calculator |
| 43 | `tests/unit/risk/test_dimensions.py` | Create | Cada dimensão com mock de fonte (APP sim/não, IPTU valor, etc.) | risk/dimensions |
| 44 | `tests/unit/risk/test_sources_cnj.py` | Create | CNJ client: happy path, 429, timeout, endereço fallback | risk/sources/cnj |
| 45 | `tests/integration/test_calculate_risk.py` | Create | Job completo: evento → score persistido → risk-change publicado | jobs/calculate_risk |
| 46 | `tests/fixtures/risk/cnj_response.json` | Create | Mock resposta CNJ com 2 processos | — |
| 47 | `tests/fixtures/risk/ibge_sidra.json` | Create | Mock resposta IBGE SIDRA (IDH, pop.) | — |
| 48 | `tests/fixtures/risk/ibama_app.geojson` | Create | Mini GeoJSON de APP para spatial join no teste | — |

**Total de arquivos: 48**

---

## Code Patterns

### Pattern 1: Interface de Dimensão

```python
# app/risk/dimensions/juridico.py
from dataclasses import dataclass, field
from app.risk.schemas import DimensionScore, RiskIndicator

_CLASSES_IMOVEIS = {
    "execucao_fiscal", "inventario", "usucapiao",
    "reintegracao_posse", "despejo", "arresto",
}

def score_juridico(
    cnpj_owner: str | None,
    address: str,
    city: str,
    state: str,
    cnj_client,          # injetado para testabilidade
) -> DimensionScore:
    indicators: list[RiskIndicator] = []
    points = 0.0
    partial = False

    try:
        processos = cnj_client.search(
            cnpj=cnpj_owner, address=address, city=city, state=state,
            classes=_CLASSES_IMOVEIS,
        )
    except Exception:
        partial = True
        processos = []

    ativos = [p for p in processos if p["status"] == "ativo"]
    if ativos:
        points += min(len(ativos) * 10, 40)
        indicators.append(RiskIndicator(
            code="A1", value=len(ativos),
            source="CNJ Datajud", date_fetched=...,
        ))

    # Detectar inventário
    inv = [p for p in ativos if "inventario" in p.get("classe", "").lower()]
    if inv:
        points += 15
        indicators.append(RiskIndicator(code="A2", value=len(inv), source="CNJ Datajud", ...))

    return DimensionScore(
        code="A", name="juridico",
        raw_points=min(points, 100),
        indicators=indicators,
        partial=partial,
    )
```

### Pattern 2: Schemas Pydantic

```python
# app/risk/schemas.py
from datetime import date
from typing import Any
from pydantic import BaseModel

class RiskIndicator(BaseModel):
    code: str               # ex: "A1", "B3", "E2"
    value: Any              # int, bool, float, str
    source: str             # ex: "CNJ Datajud", "IBGE Censo 2022"
    date_fetched: date
    note: str | None = None

class DimensionScore(BaseModel):
    code: str               # "A" .. "F"
    name: str               # "juridico" .. "mercado"
    raw_points: float       # 0-100 antes da ponderação
    indicators: list[RiskIndicator]
    partial: bool = False   # True se alguma fonte falhou

class RiskLevel(str):       # StrEnum Python 3.12
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"

class RiskScoreResult(BaseModel):
    score_total: float
    risk_level: str
    score_juridico: float
    score_fundiario: float
    score_fiscal: float
    score_ocupacao: float
    score_socioeconomico: float
    score_mercado: float
    score_partial: bool
    indicators: dict[str, RiskIndicator]  # key = indicator code
    calculation_version: str = "1.0"
    sources_consulted: list[str]
```

### Pattern 3: Orquestrador `calculate_risk()`

```python
# app/risk/calculator.py
_WEIGHTS = {"A": 0.30, "B": 0.20, "C": 0.20, "D": 0.15, "E": 0.10, "F": 0.05}

def calculate_risk(
    prop: Property,
    session: Session,
    settings: Settings | None = None,
) -> RiskScoreResult:
    s = settings or get_settings()

    # Extração do edital (Fase 2) — pode ser None
    extraction = _load_edital_extraction(session, prop.id)

    # Clientes (injetáveis em teste via override)
    cnj = CnjClient(timeout=s.risk_cnj_timeout_s)
    geo = GeoLookup(session)
    transp = TransparenciaClient()
    ibge = IbgeLookup(session)
    ipea = IpeaAtlas()

    dims = [
        score_juridico(extraction, prop, cnj),
        score_fundiario(prop, geo),
        score_fiscal(prop, transp),
        score_ocupacao(prop, extraction, session),
        score_socioeconomico(prop, ibge, ipea),
        score_mercado(prop),                     # falha silenciosa
    ]

    total = sum(d.raw_points * _WEIGHTS[d.code] for d in dims)
    total = min(max(total, 0.0), 100.0)

    return RiskScoreResult(
        score_total=round(total, 1),
        risk_level=_classify(total),
        score_juridico=dims[0].raw_points,
        score_fundiario=dims[1].raw_points,
        score_fiscal=dims[2].raw_points,
        score_ocupacao=dims[3].raw_points,
        score_socioeconomico=dims[4].raw_points,
        score_mercado=dims[5].raw_points,
        score_partial=any(d.partial for d in dims),
        indicators={ind.code: ind for d in dims for ind in d.indicators},
        sources_consulted=[ind.source for d in dims for ind in d.indicators],
    )

def _classify(score: float) -> str:
    if score <= 20: return "low"
    if score <= 40: return "moderate"
    if score <= 60: return "elevated"
    if score <= 80: return "high"
    return "critical"
```

### Pattern 4: Job `calculate_risk.py` (padrão Fase 2)

```python
# jobs/calculate_risk.py  — estrutura idêntica a process_editais.py
def process_message(session: Session, event: dict) -> str:
    property_id = uuid.UUID(event["property_id"])
    prop = session.query(Property).filter_by(id=property_id).first()
    if not prop:
        return "ignored"

    prev = session.query(PropertyRiskScore).filter_by(property_id=property_id).first()
    prev_score = prev.score_total if prev else None

    result = calculate_risk(prop, session)

    if prev:
        prev.score_total = result.score_total
        # ... atualiza todos os campos
    else:
        session.add(PropertyRiskScore(property_id=property_id, **result.model_dump()))
    session.commit()

    if prev_score is not None and abs(result.score_total - prev_score) > settings.risk_score_change_threshold:
        publish_event("risk-change-events", {
            "property_id": str(property_id),
            "old_score": prev_score,
            "new_score": result.score_total,
            "old_level": prev.risk_level,
            "new_level": result.risk_level,
        })

    return "done"
```

### Pattern 5: Endpoint heatmap GeoJSON

```python
# app/api/routes/risk.py
@router.get("/map/risk-heatmap")
def risk_heatmap(
    uf: str | None = Query(None),
    db: Session = Depends(get_db),
):
    # Agrega score médio por município
    q = (
        db.query(
            Property.city,
            Property.state,
            func.avg(PropertyRiskScore.score_total).label("risk_avg"),
            func.count(Property.id).label("property_count"),
        )
        .join(PropertyRiskScore, PropertyRiskScore.property_id == Property.id)
        .filter(Property.status == "active")
        .group_by(Property.city, Property.state)
    )
    if uf:
        q = q.filter(Property.state == uf.upper())

    rows = q.all()
    features = [
        {
            "type": "Feature",
            "properties": {
                "city": r.city, "state": r.state,
                "risk_avg": round(r.risk_avg, 1),
                "property_count": r.property_count,
            },
            "geometry": None,  # frontend faz join com GeoJSON de municípios
        }
        for r in rows
    ]
    return {"type": "FeatureCollection", "features": features}
```

### Pattern 6: Modelo SQLAlchemy

```python
# app/models/risk.py
class PropertyRiskScore(Base):
    __tablename__ = "property_risk_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id"),
        nullable=False, unique=True,  # 1 score ativo por imóvel
    )
    score_total: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    score_juridico: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    score_fundiario: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    score_fiscal: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    score_ocupacao: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    score_socioeconomico: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    score_mercado: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    indicators: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    score_partial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sources_consulted: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    calculation_version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    calculated_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, default=utcnow, nullable=False)
```

### Pattern 7: RiskMap Leaflet

```tsx
// frontend/components/RiskMap.tsx
"use client";
import { useEffect, useRef } from "react";
import type { RiskHeatmapFeature } from "@/lib/types";

const RISK_COLORS = {
  low: "#22c55e", moderate: "#eab308",
  elevated: "#f97316", high: "#ef4444", critical: "#18181b",
};

export function RiskMap({ features }: { features: RiskHeatmapFeature[] }) {
  const mapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mapRef.current) return;
    const L = require("leaflet");
    require("leaflet.heat");

    const map = L.map(mapRef.current).setView([-15, -50], 4);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);

    const heatPoints = features.map(f => [
      f.properties.lat, f.properties.lng,
      f.properties.risk_avg / 100,   // leaflet.heat usa 0-1
    ]);
    L.heatLayer(heatPoints, { radius: 35, blur: 20, maxZoom: 10 }).addTo(map);

    return () => { map.remove(); };
  }, [features]);

  return <div ref={mapRef} className="w-full h-full rounded-lg" />;
}
```

---

## Settings novas (`app/core/config.py`)

```python
# Risco — pesos das dimensões
risk_weight_juridico: float = 0.30
risk_weight_fundiario: float = 0.20
risk_weight_fiscal: float = 0.20
risk_weight_ocupacao: float = 0.15
risk_weight_socioeconomico: float = 0.10
risk_weight_mercado: float = 0.05

# Risco — thresholds de alerta
risk_score_change_threshold: float = 10.0   # pts para publicar risk-change-events

# Risco — Pub/Sub
pubsub_topic_risk: str = "risk-events"
pubsub_sub_risk: str = "risk-events-sub"
pubsub_topic_risk_changes: str = "risk-change-events"

# Risco — timeouts de fontes externas
risk_cnj_timeout_s: int = 15
risk_ibge_timeout_s: int = 10
risk_transparencia_timeout_s: int = 10
risk_fipe_timeout_s: int = 8

# Risco — indicadores (configuráveis sem redeploy)
risk_homicide_threshold_high: int = 30       # por 100k hab
risk_homicide_threshold_medium: int = 15
risk_idh_threshold_low: float = 0.650
risk_idh_threshold_medium: float = 0.750
risk_pop_decline_threshold: float = 0.05     # 5% em 10 anos
risk_iptu_debt_ratio_high: float = 0.30      # 30% do valor venal
risk_cnpj_address_penalty: int = 15
```

---

## Migration 006

```python
# migrations/versions/006_risk_scores.py
def upgrade() -> None:
    # property_risk_scores — 1 score ativo por imóvel
    op.create_table(
        "property_risk_scores",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("property_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("properties.id"), nullable=False, unique=True),
        sa.Column("score_total", sa.Numeric(5, 1), nullable=False),
        sa.Column("score_juridico", sa.Numeric(5, 1), nullable=False),
        sa.Column("score_fundiario", sa.Numeric(5, 1), nullable=False),
        sa.Column("score_fiscal", sa.Numeric(5, 1), nullable=False),
        sa.Column("score_ocupacao", sa.Numeric(5, 1), nullable=False),
        sa.Column("score_socioeconomico", sa.Numeric(5, 1), nullable=False),
        sa.Column("score_mercado", sa.Numeric(5, 1), nullable=False),
        sa.Column("risk_level", sa.String(10), nullable=False),
        sa.Column("indicators", pg.JSON, nullable=False),
        sa.Column("score_partial", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sources_consulted", pg.ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column("calculation_version", sa.String(10), nullable=False, server_default="1.0"),
        sa.Column("calculated_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index("ix_risk_scores_risk_level", "property_risk_scores", ["risk_level"])
    op.create_index("ix_risk_scores_score_total", "property_risk_scores", ["score_total"])

    # risk_geodata_layers — shapefiles em PostGIS (carregados por job de ingestão mensal)
    op.create_table(
        "risk_geodata_layers",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("layer_type", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("geom", geo_column("GEOMETRY", srid=4326), nullable=False),
        sa.Column("attributes", pg.JSON, nullable=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("loaded_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index("ix_risk_geodata_layer_type", "risk_geodata_layers", ["layer_type"])
    # Índice espacial (GIST)
    op.execute("CREATE INDEX ix_risk_geodata_geom ON risk_geodata_layers USING GIST (geom)")

    # ibge_municipality_stats — dados por município (bulk mensal)
    op.create_table(
        "ibge_municipality_stats",
        sa.Column("ibge_code", sa.String(7), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("idh", sa.Numeric(4, 3), nullable=True),
        sa.Column("homicide_rate", sa.Numeric(6, 2), nullable=True),
        sa.Column("population_2022", sa.Integer, nullable=True),
        sa.Column("population_2010", sa.Integer, nullable=True),
        sa.Column("avg_household_income", sa.Numeric(10, 2), nullable=True),
        sa.Column("vacancy_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
```

---

## API Endpoints

| Método | Endpoint | Auth | Descrição |
|--------|----------|------|-----------|
| `GET` | `/api/v1/properties/{id}/risk` | JWT | Score completo + indicadores auditáveis |
| `GET` | `/api/v1/map/risk-heatmap?uf=SP` | JWT | FeatureCollection com `risk_avg` por cidade |
| `GET` | `/api/v1/map/layers/{layer_type}` | JWT | GeoJSON de camada estática (APP, CEMADEN, etc.) |
| `GET` | `/api/v1/properties/{id}/risk/report` | JWT | StreamingResponse PDF WeasyPrint |
| `POST` | `/api/v1/admin/recalculate-risk/{id}` | JWT admin | Força recálculo; republica `risk-events` |

---

## Testing Strategy

| Tipo | Escopo | Ferramenta | Cobertura alvo |
|------|--------|------------|----------------|
| Unit — calculator | Fórmula, pesos, normalização, `score_partial` | pytest + mock | 100% das branches do calculator |
| Unit — dimensions | Cada dimensão com mock da fonte (sim/não, valores) | pytest + monkeypatch | A, B, C, D, E independentemente |
| Unit — CNJ client | happy path, 429 retry, timeout, fallback address | pytest + httpx mock | 5 cenários |
| Integration — job | Evento → PropertyRiskScore criado → risk-change publicado | pytest + SQLite + mock Pub/Sub | 3 cenários: novo, atualização, sem mudança |
| Integration — API | `/risk`, `/heatmap`, `/report` | pytest + TestClient | AT-001 a AT-008 do DEFINE |

**Nota:** A Dimensão F (Fipe ZAP) é `partial=True` em todos os testes — API externa paga/frágil; testada apenas com mock.

---

**Ready for:** `/build .claude/sdd/features/DESIGN_MAPA_RISCO_IMOVEIS.md`
