# DESIGN: Fase 5 — Leilões Judiciais + Inteligência de Mercado

> Arquitetura técnica completa para cobertura de tribunais (TRT/TRF/TJ), detector de 2ª praça, novos leiloeiros (Lance Certo, Superleilões), calculadora ROI, preço/m² via FipeZap e Radar Index granular por município.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FASE5_JUDICIAL_MERCADO |
| **Date** | 2026-06-14 |
| **Author** | design-agent |
| **DEFINE** | DEFINE_FASE5_JUDICIAL_MERCADO.md |
| **BRAINSTORM** | BRAINSTORM_FASE5_JUDICIAL_MERCADO.md |
| **Baseia-se em** | DESIGN_FASE3_TODOS_BANCOS.md + DESIGN_FASE2_IA_EDITAIS.md |
| **Status** | Ready for Build |

> **Nota de confiança:** 0.87 — a arquitetura reutiliza extensamente o pipeline existente (BankConnector, collect_bank.py, change_detector, Pub/Sub). As incógnitas concentram-se nos formatos de resposta de Lance Certo, Superleilões e na estrutura exata dos hits DataJud para hastas — isolados em parsers validados no momento do build.

---

## 1. Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                  RADAR IMÓVEL — FASE 5 (JUDICIAL + MERCADO)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Cloud Scheduler (novos jobs)                                          │  │
│  │  collect-judicial-trt2   collect-judicial-trf3   collect-judicial-tjsp │  │
│  │  collect-lance-certo     collect-superleiloes                          │  │
│  │  collect-market-prices   (mensal)                                      │  │
│  └──────────────────────────────┬────────────────────────────────────────┘  │
│                                  │                                           │
│                                  ▼                                           │
│                     ┌─────────────────────┐                                 │
│                     │  Pub/Sub             │                                 │
│                     │  collect-trigger     │  (reuso — sem mudança)          │
│                     └──────────┬──────────┘                                 │
│                                │                                             │
│         ┌──────────────────────┴───────────────────────────┐               │
│         ▼                                                    ▼               │
│  ┌──────────────────────┐              ┌─────────────────────────────────┐  │
│  │  Cloud Run Job        │              │  Cloud Run Job                  │  │
│  │  radar-collect-bank  │              │  radar-collect-judicial          │  │
│  │  (BANK=lance_certo   │              │  (TRIBUNAL=TRT2|TRF3|TJSP)      │  │
│  │   BANK=superleiloes) │              │                                  │  │
│  │                      │              │  JudicialConnector               │  │
│  │  CONNECTOR_REGISTRY  │              │   ├─ DataJudClient.search_hasta()│  │
│  └──────────┬───────────┘              │   ├─ filtros tribunal+classe     │  │
│             │                          │   └─ resolve leiloeiro designado │  │
│             └──────────────┬───────────┘                                  │  │
│                            │                                               │  │
│                            ▼  (pipeline idêntico ao da Fase 3)             │  │
│  ┌────────────────────────────────────────────────────────────────────┐   │  │
│  │  score_agent  →  deduplicator  →  change_detector  →  Cloud SQL    │   │  │
│  │                                          │                          │   │  │
│  │                                          ▼  NOVO                   │   │  │
│  │                               SecondAuctionDetector                │   │  │
│  │                               (queda ≥40% minimum_value)           │   │  │
│  │                                          │                          │   │  │
│  │                                          ▼                          │   │  │
│  │                               Pub/Sub property-events               │   │  │
│  │                               (event_type: new|changed|segunda_praca│   │  │
│  └──────────────────────────────────────────┬───────────────────────┘   │  │
│                                              │                              │  │
│  ┌───────────────────────────────────────────┼──────────────────────────┐  │  │
│  │  NOVOS SERVIÇOS (Fase 5)                  │                           │  │  │
│  │                                           ▼                           │  │  │
│  │  ┌──────────────────────┐   ┌────────────────────────────────────┐  │  │  │
│  │  │  Cloud Run Job        │   │  FastAPI — novos endpoints          │  │  │  │
│  │  │  collect-market-      │   │  GET /market-prices                 │  │  │  │
│  │  │  prices (mensal)      │   │  POST /properties/{id}/roi          │  │  │  │
│  │  │                       │   │  GET /radar-index?granularity=city  │  │  │  │
│  │  │  FipeZapClient        │   │  GET /radar-index/hotspots          │  │  │  │
│  │  │  → market_prices DB   │   │  GET /properties/{id}/report (PDF)  │  │  │  │
│  │  └──────────────────────┘   └────────────────────────────────────┘  │  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Componentes (delta sobre Fase 3/4)

| Componente | Status | Propósito |
|------------|--------|-----------|
| `app/connectors/judicial/` | **Novo** | JudicialConnector via DataJud — TRT, TRF, TJs |
| `app/connectors/lance_certo/` | **Novo** | Leiloeiro judicial de alto volume |
| `app/connectors/superleiloes/` | **Novo** | Leiloeiro misto (judicial + extrajudicial) |
| `app/agents/second_auction_detector.py` | **Novo** | Detecta 2ª praça por queda ≥40% no minimum_value |
| `app/services/fipezap.py` | **Novo** | Client FipeZap para preço/m² por cidade |
| `app/calculator/roi.py` | **Novo** | Lógica de cálculo ROI (revenda/aluguel/moradia) |
| `jobs/collect_judicial.py` | **Novo** | Job de coleta de hastas judiciais |
| `jobs/collect_market_prices.py` | **Novo** | Job mensal de preços de mercado FipeZap |
| `app/api/routes/market.py` | **Novo** | Endpoints `/market-prices` e `/roi` |
| `migrations/versions/012_fase5_judicial.py` | **Novo** | `market_prices` + colunas em `properties` |
| `frontend/app/imoveis/[id]/roi/` | **Novo** | Página calculadora ROI |
| `frontend/components/MarketComparisonBadge.tsx` | **Novo** | Badge "X% abaixo do mercado" |
| `frontend/components/SecondAuctionBadge.tsx` | **Novo** | Badge "2ª Praça" em vermelho |
| `SecondAuctionDetector` | **Novo** | Agente acoplado ao change_detector |
| `DataJudClient` (expansão) | **Modificar** | Adicionar filtros de tribunal + classe processual |
| `CONNECTOR_REGISTRY` | **Modificar** | Adicionar lance_certo, superleiloes |
| `collect_bank.py` | **Reuso** | Roda Lance Certo e Superleilões via BANK env |
| `radar-index` endpoint | **Modificar** | Suporte a `granularity=city` + campo `trend` |
| `pdf_report.py` | **Modificar** | Expandir com preço/m², processos, edital IA |
| `alert_agent` | **Modificar** | Template para evento `segunda_praca` |
| Pub/Sub `property-events` | **Reuso** | Sem mudança de schema |
| Pipeline de score/dedup/change | **Reuso** | Bank-agnostic já |

---

## 2. File Manifest

### Backend — Python

| # | Arquivo | Ação | Agente |
|---|---------|------|--------|
| 1 | `app/connectors/judicial/__init__.py` | CREATE | @python-developer |
| 2 | `app/connectors/judicial/collector.py` | CREATE | @python-developer |
| 3 | `app/connectors/judicial/parser.py` | CREATE | @python-developer |
| 4 | `app/connectors/judicial/normalizer.py` | CREATE | @python-developer |
| 5 | `app/connectors/lance_certo/__init__.py` | CREATE | @python-developer |
| 6 | `app/connectors/lance_certo/collector.py` | CREATE | @python-developer |
| 7 | `app/connectors/lance_certo/parser.py` | CREATE | @python-developer |
| 8 | `app/connectors/lance_certo/normalizer.py` | CREATE | @python-developer |
| 9 | `app/connectors/superleiloes/__init__.py` | CREATE | @python-developer |
| 10 | `app/connectors/superleiloes/collector.py` | CREATE | @python-developer |
| 11 | `app/connectors/superleiloes/parser.py` | CREATE | @python-developer |
| 12 | `app/connectors/superleiloes/normalizer.py` | CREATE | @python-developer |
| 13 | `app/connectors/__init__.py` | MODIFY | @python-developer |
| 14 | `app/connectors/tjsp/__init__.py` | CREATE | @python-developer |
| 15 | `app/connectors/tjsp/collector.py` | CREATE | @python-developer |
| 16 | `app/connectors/tjsp/parser.py` | CREATE | @python-developer |
| 17 | `app/connectors/tjsp/normalizer.py` | CREATE | @python-developer |
| 18 | `app/agents/second_auction_detector.py` | CREATE | @python-developer |
| 19 | `app/agents/change_detector.py` | MODIFY | @python-developer |
| 20 | `app/agents/alert_agent.py` | MODIFY | @python-developer |
| 21 | `app/services/fipezap.py` | CREATE | @python-developer |
| 22 | `app/calculator/roi.py` | CREATE | @python-developer |
| 23 | `app/calculator/__init__.py` | CREATE | @python-developer |
| 24 | `app/risk/sources/datajud.py` | MODIFY | @python-developer |
| 25 | `app/risk/pdf_report.py` | MODIFY | @python-developer |
| 26 | `app/api/routes/market.py` | CREATE | @python-developer |
| 27 | `app/api/routes/properties.py` | MODIFY | @python-developer |
| 28 | `app/api/main.py` | MODIFY | @python-developer |
| 29 | `jobs/collect_judicial.py` | CREATE | @python-developer |
| 30 | `jobs/collect_market_prices.py` | CREATE | @python-developer |

### Migrations — Alembic

| # | Arquivo | Ação |
|---|---------|------|
| 31 | `migrations/versions/012_fase5_judicial.py` | CREATE |

### Tests

| # | Arquivo | Ação |
|---|---------|------|
| 32 | `tests/unit/connectors/test_judicial_parser.py` | CREATE |
| 33 | `tests/unit/connectors/test_lance_certo_parser.py` | CREATE |
| 34 | `tests/unit/connectors/test_superleiloes_parser.py` | CREATE |
| 35 | `tests/unit/agents/test_second_auction_detector.py` | CREATE |
| 36 | `tests/unit/calculator/test_roi.py` | CREATE |
| 37 | `tests/unit/services/test_fipezap.py` | CREATE |

### Infra — Terraform

| # | Arquivo | Ação |
|---|---------|------|
| 38 | `infra/terraform/cloud_run.tf` | MODIFY |
| 39 | `infra/terraform/scheduler.tf` | MODIFY |
| 40 | `infra/terraform/pubsub.tf` | MODIFY |

### Frontend — Next.js

| # | Arquivo | Ação | Agente |
|---|---------|------|--------|
| 41 | `frontend/app/imoveis/[id]/roi/page.tsx` | CREATE | @typescript-reviewer |
| 42 | `frontend/components/ROICalculator.tsx` | CREATE | @typescript-reviewer |
| 43 | `frontend/components/MarketComparisonBadge.tsx` | CREATE | @typescript-reviewer |
| 44 | `frontend/components/SecondAuctionBadge.tsx` | CREATE | @typescript-reviewer |
| 45 | `frontend/components/PropertyCard.tsx` | MODIFY | @typescript-reviewer |
| 46 | `frontend/app/mapa/page.tsx` | MODIFY | @typescript-reviewer |
| 47 | `frontend/app/radar-index/page.tsx` | MODIFY | @typescript-reviewer |

---

## 3. Schema Changes — Migration 012

```python
"""Fase 5: judicial + mercado

Revision: 012
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Nova tabela de preços de mercado
    op.create_table(
        "market_prices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("uf", sa.String(2), nullable=False),
        sa.Column("property_type", sa.String(50)),
        sa.Column("price_per_sqm_sale", sa.Numeric(12, 2)),
        sa.Column("price_per_sqm_rent", sa.Numeric(12, 2)),
        sa.Column("reference_month", sa.Date(), nullable=False),
        sa.Column("source", sa.String(50), server_default="fipezap"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "city", "uf", "property_type", "reference_month", "source",
            name="uq_market_prices"
        ),
    )

    # Novas colunas em properties
    op.add_column("properties", sa.Column("source_type", sa.String(20), server_default="bank"))
    op.add_column("properties", sa.Column("auction_stage", sa.String(30)))
    op.add_column("properties", sa.Column("auctioneer_name", sa.String(100)))
    op.add_column("properties", sa.Column("process_number", sa.String(50)))
    op.add_column("properties", sa.Column("market_price_per_sqm", sa.Numeric(12, 2)))
    op.add_column("properties", sa.Column("discount_vs_market_pct", sa.Numeric(5, 2)))

    # Índice para consultas de 2ª praça
    op.create_index("ix_properties_auction_stage", "properties", ["auction_stage"])
    # Índice para consultas judiciais
    op.create_index("ix_properties_source_type", "properties", ["source_type"])
    op.create_index("ix_properties_process_number", "properties", ["process_number"])


def downgrade():
    op.drop_index("ix_properties_process_number")
    op.drop_index("ix_properties_source_type")
    op.drop_index("ix_properties_auction_stage")
    op.drop_column("properties", "discount_vs_market_pct")
    op.drop_column("properties", "market_price_per_sqm")
    op.drop_column("properties", "process_number")
    op.drop_column("properties", "auctioneer_name")
    op.drop_column("properties", "auction_stage")
    op.drop_column("properties", "source_type")
    op.drop_table("market_prices")
```

---

## 4. JudicialConnector — Design Detalhado

### 4.1 Expansão do DataJudClient

```python
# app/risk/sources/datajud.py — MODIFY
# Adicionar suporte a filtro de tribunal e classe processual

TRIBUNAL_CODES = {
    # TRTs
    "TRT1": "trt-1-regiao",   # RJ
    "TRT2": "trt-2-regiao",   # SP (capital)
    "TRT3": "trt-3-regiao",   # MG
    "TRT4": "trt-4-regiao",   # RS
    "TRT5": "trt-5-regiao",   # BA
    "TRT15": "trt-15-regiao", # Campinas
    # ... TRT6 a TRT24
    # TRFs
    "TRF1": "trf-1-regiao",
    "TRF3": "trf-3-regiao",   # SP + MS
    # TJs
    "TJSP": "tjsp",
    "TJRJ": "tjrj",
    "TJMG": "tjmg",
    "TJRS": "tjrs",
}

HASTA_CLASS_CODES = [
    "hasta publica",
    "arrematacao",
    "penhora",
    "adjudicacao compulsoria",
    "alienacao judicial",
]

class DataJudClient:
    def search_hastas_tribunal(
        self,
        tribunal: str,
        *,
        days_back: int = 30,
        page: int = 0,
        size: int = 100,
    ) -> list[dict]:
        """Busca hastas públicas em um tribunal específico."""
        tribunal_code = TRIBUNAL_CODES.get(tribunal)
        if not tribunal_code:
            raise ValueError(f"Tribunal '{tribunal}' não mapeado")

        payload = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"tribunal": tribunal_code}},
                        {"terms": {"classeProcessual.nome": HASTA_CLASS_CODES}},
                    ],
                    "filter": [
                        {"range": {"dataAjuizamento": {
                            "gte": f"now-{days_back}d/d",
                            "lte": "now/d",
                        }}},
                    ],
                }
            },
            "from": page * size,
            "size": size,
            "_source": [
                "numeroProcesso",
                "tribunal",
                "classeProcessual",
                "assuntos",
                "dataAjuizamento",
                "orgaoJulgador",
                "movimentos",  # contém datas de hasta e valores
            ],
        }
        # POST para endpoint ElasticSearch do DataJud
        try:
            resp = httpx.post(
                f"{_BASE}/api_publica/processo/_search",
                json=payload,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
            return [self._fmt_judicial(h["_source"]) for h in hits]
        except Exception as exc:
            logger.warning("datajud_tribunal_search_error", tribunal=tribunal, error=str(exc))
            return []
```

### 4.2 JudicialConnector

```python
# app/connectors/judicial/collector.py

from app.connectors.base import BankConnector, RawProperty
from app.risk.sources.datajud import DataJudClient

_PRIORITY_TRIBUNAIS = [
    "TRT2", "TRT3", "TRT4", "TRT1", "TRT15",
    "TRF3", "TRF1",
    "TJSP", "TJRJ",
]

class JudicialConnector(BankConnector):
    bank_code = "judicial"

    def __init__(self, tribunal: str, days_back: int = 30):
        self._tribunal = tribunal
        self._days_back = days_back
        self._client = DataJudClient()

    def discover_sources(self) -> list[str]:
        # Retorna "páginas" virtuais: "TRT2:0", "TRT2:1", ...
        return [f"{self._tribunal}:{p}" for p in range(10)]  # max 1000 hits

    def fetch_raw(self, source: str) -> bytes:
        tribunal, page = source.split(":")
        hits = self._client.search_hastas_tribunal(
            tribunal, days_back=self._days_back, page=int(page)
        )
        if not hits:
            return b""
        import json
        return json.dumps(hits).encode()

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            return
        import json
        hits = json.loads(raw_bytes)
        for hit in hits:
            yield RawProperty(
                external_code=hit.get("process_number"),
                title=hit.get("summary") or f"Hasta Pública — {self._tribunal}",
                city=hit.get("city"),
                state=hit.get("state"),
                minimum_value=hit.get("minimum_value"),
                source_url=hit.get("process_url"),
                auction_date=hit.get("hasta_date"),
                extra={
                    "source_type": "judicial",
                    "process_number": hit.get("process_number"),
                    "tribunal": self._tribunal,
                    "auctioneer_name": hit.get("auctioneer"),
                },
            )

    def normalize(self, raw: RawProperty) -> dict:
        from app.connectors.judicial.normalizer import JudicialNormalizer
        return JudicialNormalizer().normalize(raw)
```

---

## 5. SecondAuctionDetector — Design Detalhado

```python
# app/agents/second_auction_detector.py

from __future__ import annotations
from decimal import Decimal

_SEGUNDA_PRACA_THRESHOLD = 0.40  # queda de 40%+ no minimum_value

class SecondAuctionDetector:
    """
    Detecta quando um imóvel vai a 2ª praça e publica evento prioritário.
    Invocado pelo change_detector imediatamente após persistir uma mudança.
    """

    def detect(
        self,
        property_id: int,
        old_minimum: Decimal | None,
        new_minimum: Decimal | None,
        old_stage: str | None,
    ) -> bool:
        """Retorna True se for 2ª praça; efeito colateral: atualiza DB + publica evento."""
        if not old_minimum or not new_minimum:
            return False
        if old_stage == "segunda_praca":
            return False  # já estava em 2ª praça

        drop = float(old_minimum - new_minimum) / float(old_minimum)
        if drop >= _SEGUNDA_PRACA_THRESHOLD:
            self._mark_segunda_praca(property_id)
            return True
        return False

    def _mark_segunda_praca(self, property_id: int) -> None:
        # UPDATE properties SET auction_stage = 'segunda_praca' WHERE id = :id
        # PUBLISH Pub/Sub property-events { event_type: 'segunda_praca', property_id, priority: 'HIGH' }
        ...
```

### Integração com change_detector

```python
# app/agents/change_detector.py — MODIFY (trecho)

from app.agents.second_auction_detector import SecondAuctionDetector

_detector = SecondAuctionDetector()

def _apply_change(session, existing: Property, new_data: dict) -> list[str]:
    changed_fields = []
    old_minimum = existing.minimum_value
    # ... lógica existente de detecção de mudanças ...

    # Novo: verificar 2ª praça após aplicar mudanças
    if "minimum_value" in changed_fields:
        _detector.detect(
            property_id=existing.id,
            old_minimum=old_minimum,
            new_minimum=existing.minimum_value,
            old_stage=existing.auction_stage,
        )
    return changed_fields
```

### Template de alerta 2ª Praça

```python
# app/agents/alert_agent.py — MODIFY

_SEGUNDA_PRACA_TEMPLATE = """
🔴 *ALERTA 2ª PRAÇA* — {title}

📍 {city}/{state}
🏦 Fonte: {source}

💰 Valor anterior: *R$ {old_value:,.0f}*
💎 Novo valor mínimo: *R$ {new_value:,.0f}*
📉 Queda: *{drop_pct:.0f}%*

⏰ Leilão: {auction_date}
🔗 {url}

_Em 2ª praça, lance mínimo é geralmente 50% do valor de avaliação._
"""
```

---

## 6. FipeZap Client — Design Detalhado

```python
# app/services/fipezap.py

import httpx
from app.core.logging import logger

_FIPEZAP_BASE = "https://fipezap.zapimoveis.com.br"

class FipeZapClient:
    """
    Coleta índice FipeZap de preço/m² por cidade.

    Estratégia primária: endpoint de dados públicos (se disponível).
    Estratégia secundária: scraping da página de índice com extração tabular.
    """

    def fetch_index(self, reference_month: str) -> list[dict]:
        """
        Retorna lista de { city, uf, property_type, price_per_sqm_sale, price_per_sqm_rent }.
        reference_month: "2026-06" (YYYY-MM)
        """
        try:
            return self._fetch_api(reference_month)
        except Exception:
            logger.warning("fipezap_api_unavailable", fallback="scraping")
            return self._fetch_scraping(reference_month)

    def _fetch_api(self, reference_month: str) -> list[dict]:
        # Endpoint público do FipeZap (validar URL real no build)
        resp = httpx.get(
            f"{_FIPEZAP_BASE}/api/v2/indicadores",
            params={"competencia": reference_month},
            timeout=30,
        )
        resp.raise_for_status()
        return self._parse_api_response(resp.json())

    def _fetch_scraping(self, reference_month: str) -> list[dict]:
        from bs4 import BeautifulSoup
        resp = httpx.get(f"{_FIPEZAP_BASE}/indices", timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        return self._parse_html_table(soup)

    def _parse_api_response(self, data: dict) -> list[dict]:
        results = []
        for item in data.get("items", []):
            results.append({
                "city": item.get("cidade"),
                "uf": item.get("uf"),
                "property_type": item.get("tipo", "geral"),
                "price_per_sqm_sale": item.get("precoVendaM2"),
                "price_per_sqm_rent": item.get("precoLocacaoM2"),
            })
        return results
```

---

## 7. Calculadora ROI — Design Detalhado

```python
# app/calculator/roi.py

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.core.logging import logger

Intention = Literal["revenda", "aluguel", "moradia"]

@dataclass
class ROIInput:
    lance_value: Decimal
    area_sqm: float | None
    reform_cost_per_sqm: Decimal
    horizon_months: int
    intention: Intention
    market_price_per_sqm_sale: Decimal | None
    market_price_per_sqm_rent: Decimal | None
    selic_annual: Decimal  # ex: 0.1065 para 10.65%

@dataclass
class ROIResult:
    roi_pct: float | None
    yield_annual_pct: float | None
    payback_months: float | None
    cdi_equivalent_pct: float
    net_gain_vs_cdi_pct: float | None
    assumptions: dict  # valores usados no cálculo para transparência

_ITBI_REGISTRY = 0.04    # ITBI + registro estimado em 4%
_VACANT_MONTHS = 1       # meses vagos por ano estimado (conservador)
_ADMIN_FEE = 0.08        # taxa de administração de aluguel (8%)

def calculate_roi(inp: ROIInput) -> ROIResult:
    reform_total = Decimal(str(inp.area_sqm or 0)) * inp.reform_cost_per_sqm
    total_invested = inp.lance_value + reform_total

    roi_pct: float | None = None
    yield_annual_pct: float | None = None
    payback_months: float | None = None

    if inp.intention == "revenda" and inp.market_price_per_sqm_sale and inp.area_sqm:
        market_value = Decimal(str(inp.area_sqm)) * inp.market_price_per_sqm_sale
        transaction_costs = total_invested * Decimal(str(_ITBI_REGISTRY))
        net_gain = market_value - total_invested - transaction_costs
        roi_pct = float(net_gain / total_invested * 100)

    elif inp.intention == "aluguel" and inp.market_price_per_sqm_rent and inp.area_sqm:
        gross_monthly_rent = Decimal(str(inp.area_sqm)) * inp.market_price_per_sqm_rent
        effective_monthly = gross_monthly_rent * Decimal(str(1 - _ADMIN_FEE))
        # Descontar vacância anual
        annual_rent = effective_monthly * Decimal(str(12 - _VACANT_MONTHS))
        yield_annual_pct = float(annual_rent / total_invested * 100)
        if effective_monthly > 0:
            payback_months = float(total_invested / effective_monthly)

    # CDI/Selic no mesmo horizonte
    cdi_pct = float(inp.selic_annual * inp.horizon_months / 12 * 100)
    comparable = roi_pct or yield_annual_pct
    net_gain_vs_cdi = (comparable - cdi_pct) if comparable is not None else None

    return ROIResult(
        roi_pct=roi_pct,
        yield_annual_pct=yield_annual_pct,
        payback_months=payback_months,
        cdi_equivalent_pct=cdi_pct,
        net_gain_vs_cdi_pct=net_gain_vs_cdi,
        assumptions={
            "total_invested": float(total_invested),
            "reform_total": float(reform_total),
            "itbi_registry_pct": _ITBI_REGISTRY * 100,
            "selic_annual_pct": float(inp.selic_annual * 100),
        },
    )
```

### Endpoint FastAPI

```python
# app/api/routes/market.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.calculator.roi import ROIInput, ROIResult, calculate_roi, Intention
from app.services.fipezap import get_market_prices_for_city
from app.risk.sources.transparencia import get_selic_rate

router = APIRouter(prefix="/market", tags=["market"])

class ROIRequest(BaseModel):
    intention: Intention
    reform_cost_per_sqm: float = 500.0
    horizon_months: int = 24

@router.post("/properties/{property_id}/roi", response_model=dict)
async def roi_calculator(property_id: int, req: ROIRequest, session=Depends(get_session)):
    prop = session.get(Property, property_id)
    if not prop:
        raise HTTPException(404, "Imóvel não encontrado")

    market = await get_market_prices_for_city(prop.city, prop.state, prop.property_type)
    selic = await get_selic_rate()

    inp = ROIInput(
        lance_value=prop.current_value or prop.minimum_value,
        area_sqm=prop.area_sqm,
        reform_cost_per_sqm=req.reform_cost_per_sqm,
        horizon_months=req.horizon_months,
        intention=req.intention,
        market_price_per_sqm_sale=market.price_per_sqm_sale if market else None,
        market_price_per_sqm_rent=market.price_per_sqm_rent if market else None,
        selic_annual=selic,
    )
    return calculate_roi(inp).__dict__

@router.get("/market-prices")
async def market_prices(city: str, uf: str, property_type: str = "geral", session=Depends(get_session)):
    # Busca mais recente da tabela market_prices
    ...
```

---

## 8. Radar Index Granular — Design

### SQL de agregação por município

```sql
-- Novo endpoint: GET /radar-index?granularity=city
SELECT
    city,
    uf,
    DATE_TRUNC('month', collected_at) AS period,
    COUNT(*) AS sample_size,
    AVG(discount_percent) AS avg_discount_pct,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY discount_percent) AS median_discount_pct,
    -- Tendência: comparar com mês anterior
    AVG(discount_percent) - LAG(AVG(discount_percent)) OVER (
        PARTITION BY city, uf
        ORDER BY DATE_TRUNC('month', collected_at)
    ) AS trend_delta
FROM properties
WHERE
    discount_percent IS NOT NULL
    AND collected_at >= NOW() - INTERVAL '2 months'
    AND city IS NOT NULL
GROUP BY city, uf, DATE_TRUNC('month', collected_at)
ORDER BY avg_discount_pct DESC;
```

### Hotspots endpoint

```python
# GET /radar-index/hotspots
# Retorna top 10 municípios com maior deságio médio nos últimos 30 dias
# Mínimo de 5 imóveis no período (sample_size >= 5)
```

---

## 9. Lance Certo Connector — Design

```python
# app/connectors/lance_certo/collector.py

_BASE_URL = "https://www.lancecerto.com.br"
_IMOVEL_CATEGORIES = ["imoveis", "imovel-residencial", "imovel-comercial"]

class LanceCertoCollector:
    """
    Lance Certo é especializado em leilões judiciais.
    O portal tem paginação via query params e responde sem JS (HTML server-rendered).
    Estratégia: httpx com headers de browser; Playwright se 403.
    """

    def collect(self, category: str = "imoveis", page: int = 1) -> bytes:
        url = f"{_BASE_URL}/leiloes/{category}"
        params = {"page": page, "sort": "data_asc"}
        try:
            resp = httpx.get(url, params=params, headers=_BROWSER_HEADERS, timeout=20)
            if resp.status_code == 403:
                return self._collect_playwright(url, params)
            resp.raise_for_status()
            return resp.content
        except Exception as exc:
            logger.warning("lance_certo_collect_error", url=url, error=str(exc))
            return b""
```

---

## 10. Superleilões Connector — Design

```python
# app/connectors/superleiloes/collector.py

_BASE_URL = "https://www.superleiloes.com.br"

class SuperleiloesCollector:
    """
    Superleilões é React SPA — requer Playwright.
    Estratégia: navegar para listagem de imóveis, aguardar React renderizar,
    interceptar chamada XHR/fetch da API interna (similar ao BRB/Resale).
    """

    def collect(self, page: int = 1) -> bytes:
        from app.connectors.playwright_utils import get_browser_context
        with get_browser_context(stealth=False) as ctx:
            page_obj = ctx.new_page()
            api_response_data: list[dict] = []

            def intercept(response):
                if "/api/lotes" in response.url and response.status == 200:
                    try:
                        api_response_data.extend(response.json().get("lotes", []))
                    except Exception:
                        pass

            page_obj.on("response", intercept)
            page_obj.goto(f"{_BASE_URL}/imoveis?page={page}")
            page_obj.wait_for_load_state("networkidle", timeout=30000)

            if api_response_data:
                import json
                return json.dumps(api_response_data).encode()

            # Fallback: extrair HTML renderizado
            return page_obj.content().encode()
```

---

## 11. Terraform Changes

### `cloud_run.tf` — Novo job judicial

```hcl
resource "google_cloud_run_v2_job" "collect_judicial" {
  name     = "radar-collect-judicial"
  location = var.region

  template {
    template {
      containers {
        image = "${var.artifact_registry}/radar-imovel-job:latest"
        command = ["python", "-m", "jobs.collect_judicial"]

        env {
          name  = "TRIBUNAL"
          value = "TRT2"  # overridden per scheduler
        }
        env {
          name  = "DAYS_BACK"
          value = "30"
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
      }
      service_account = google_service_account.cloud_run_jobs.email
    }
  }
}

resource "google_cloud_run_v2_job" "collect_market_prices" {
  name     = "radar-collect-market-prices"
  location = var.region

  template {
    template {
      containers {
        image   = "${var.artifact_registry}/radar-imovel-job:latest"
        command = ["python", "-m", "jobs.collect_market_prices"]
        resources { limits = { cpu = "1", memory = "512Mi" } }
      }
      service_account = google_service_account.cloud_run_jobs.email
    }
  }
}
```

### `scheduler.tf` — Novos schedulers

```hcl
# TRTs prioritários — diário às 06:00
locals {
  judicial_tribunais = ["TRT2", "TRT3", "TRT4", "TRT1", "TRT15", "TRF3", "TJSP"]
}

resource "google_cloud_scheduler_job" "collect_judicial" {
  for_each = toset(local.judicial_tribunais)

  name      = "collect-judicial-${lower(each.key)}"
  schedule  = "0 6 * * *"
  time_zone = "America/Sao_Paulo"

  http_target {
    uri        = "https://run.googleapis.com/v2/${google_cloud_run_v2_job.collect_judicial.id}:run"
    http_method = "POST"
    body = base64encode(jsonencode({
      overrides = {
        containerOverrides = [{
          env = [{ name = "TRIBUNAL", value = each.key }]
        }]
      }
    }))
    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
}

# Lance Certo + Superleilões — via job genérico collect_bank
resource "google_cloud_scheduler_job" "collect_lance_certo" {
  name     = "collect-lance-certo"
  schedule = "0 7 * * *"
  # ... igual aos outros bancos no scheduler.tf existente
}

# Preços de mercado — mensal (dia 1, 08:00)
resource "google_cloud_scheduler_job" "collect_market_prices" {
  name      = "collect-market-prices"
  schedule  = "0 8 1 * *"
  time_zone = "America/Sao_Paulo"
  # ...
}
```

---

## 12. Frontend — Componentes Chave

### SecondAuctionBadge.tsx

```tsx
// frontend/components/SecondAuctionBadge.tsx
export function SecondAuctionBadge() {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full
                     bg-red-100 text-red-800 text-xs font-bold border border-red-300
                     animate-pulse">
      🔴 2ª Praça
    </span>
  );
}
```

### MarketComparisonBadge.tsx

```tsx
// frontend/components/MarketComparisonBadge.tsx
interface Props {
  discountVsMarketPct: number | null;
}

export function MarketComparisonBadge({ discountVsMarketPct }: Props) {
  if (!discountVsMarketPct) return null;
  const color =
    discountVsMarketPct >= 30 ? "bg-green-100 text-green-800 border-green-300" :
    discountVsMarketPct >= 15 ? "bg-yellow-100 text-yellow-800 border-yellow-300" :
    "bg-gray-100 text-gray-600 border-gray-200";

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${color}`}>
      {discountVsMarketPct.toFixed(0)}% abaixo do mercado
    </span>
  );
}
```

### ROICalculator.tsx (modal)

```tsx
// frontend/components/ROICalculator.tsx
// Modal com inputs: intenção (radio), custo reforma (slider 0–2000 R$/m²),
// horizonte (select 12/24/36/60 meses)
// Output: cards com ROI%, Yield%, Payback, Comparativo CDI
// Implementar com React state + fetch para POST /properties/{id}/roi
```

---

## 13. Key Decisions

### Decision 1: JudicialConnector usa DataJudClient existente como fonte primária de coleta

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06-14 |

**Context:** O `DataJudClient` foi criado como fonte de *risco* (verificar se um imóvel tem processo vinculado). A Fase 5 o reposiciona como fonte de *coleta* — descobrir hastas públicas e trazê-las para o pipeline.

**Choice:** Reusar o cliente existente com novos métodos (`search_hastas_tribunal`) em vez de criar um cliente paralelo.

**Rationale:** O cliente já lida com autenticação, timeout, rate limiting e parsing de formato ElasticSearch do CNJ. Adicionar métodos de filtro por tribunal é evolução natural, não quebra contrato existente.

**Alternatives Rejected:**
1. **Scraping dos portais individuais de cada TRT** — 24 portais com layouts distintos, altíssima manutenção; DataJud é a fonte canônica e unificada.
2. **Novo cliente separado para coleta judicial** — duplicação; `DataJudClient` já tem toda a lógica de HTTP/retry.

**Consequences:**
- `app/risk/sources/datajud.py` ganha método `search_hastas_tribunal()` 
- O arquivo permanece em `risk/sources/` (não muda de lugar) mas tem dupla responsabilidade (risco + coleta)
- Risco aceito: se o DataJud mudar sua API ElasticSearch, tanto a coleta quanto o risco são impactados — aceito pois é fonte oficial do CNJ

---

### Decision 2: SecondAuctionDetector acoplado ao change_detector (não job separado)

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06-14 |

**Context:** A detecção de 2ª praça é um evento síncrono com a detecção de mudança de preço — deve acontecer no mesmo ciclo de processamento, não com delay de job separado.

**Choice:** O `SecondAuctionDetector.detect()` é chamado diretamente dentro do `change_detector` após persistir a mudança.

**Rationale:** Latência zero entre detectar a queda e publicar o alerta P0. Investidores competem por 2ª praça — delay de minutos pode custar a oportunidade.

**Alternatives Rejected:**
1. **Job Cron separado que verifica 2ª praça** — delay de até 1h entre a coleta e o alerta; não adequado para evento time-sensitive.
2. **Pub/Sub separado `price-drop-events`** — complexidade desnecessária; o evento `segunda_praca` no tópico `property-events` existente já é suficiente com o campo `priority`.

---

### Decision 3: FipeZap como fonte de mercado (não scraping de portais imobiliários)

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06-14 |

**Context:** Alternativas para preço de mercado: (1) FipeZap — índice consolidado mensal; (2) Scraping de ZAP Imóveis/Viva Real — dados frescos mas ToS questionável; (3) Dados IBGE — desatualizados.

**Choice:** FipeZap como fonte primária.

**Rationale:** FipeZap publica dados mensais oficiais com metodologia pública. Cobertura de 50+ cidades brasileiras. Não há problemas de ToS pois os dados são publicados como índice público. Granularidade suficiente para o cálculo de comparativo (nível cidade/tipo).

**Limitations aceitas:** Atualização mensal (não em tempo real); cobertura restrita a ~50 cidades grandes (cidades menores retornam "sem dado FipeZap").

**Fallback:** Para cidades sem dado FipeZap, usar a média do estado como proxy.

---

### Decision 4: TJSP usa DataJud + resolve leiloeiro designado (não scraping do portal e-leilões TJSP)

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06-14 |

**Context:** O portal e-leilões do TJSP exige cadastro e tem proteção WAF. Alternativamente, o DataJud retorna processos do TJSP e os leiloeiros credenciados (Fidalgo, Sodré, Mega, Zuk) já são cobertos pelos conectores existentes.

**Choice:** `TJSPConnector` = `JudicialConnector` com `TRIBUNAL=TJSP` (não conector separado).

**Rationale:** DRY — a lógica de filtro do DataJud por tribunal é idêntica para qualquer TJ. O TJSP entra como um valor de `TRIBUNAL_CODES`. O diretório `app/connectors/tjsp/` implementa apenas a normalização específica do TJSP (mapeamento de campos e resolução de leiloeiro designado), delegando a coleta ao JudicialConnector.

---

## 14. Test Plan

### Unitários

| Teste | Comportamento |
|-------|---------------|
| `test_second_auction_detector.py::test_queda_40pct_dispara_evento` | Queda de 40% → `detect()` retorna True + evento publicado |
| `test_second_auction_detector.py::test_queda_39pct_nao_dispara` | Queda de 39% → retorna False |
| `test_second_auction_detector.py::test_ja_em_segunda_praca_ignora` | `auction_stage = segunda_praca` → retorna False |
| `test_judicial_parser.py::test_parse_datajud_hit` | JSON hit DataJud → `RawProperty` com campos corretos |
| `test_judicial_parser.py::test_parse_vazio` | `b""` → iterator vazio, sem exceção |
| `test_roi.py::test_revenda_calcula_roi` | Input válido revenda → ROI positivo calculado corretamente |
| `test_roi.py::test_aluguel_calcula_yield` | Input válido aluguel → yield e payback corretos |
| `test_roi.py::test_sem_area_retorna_none` | `area_sqm=None` → roi/yield = None, sem exceção |
| `test_fipezap.py::test_parse_api_response` | JSON mock FipeZap → lista de preços parseada |
| `test_lance_certo_parser.py::test_parse_html` | HTML mock Lance Certo → lista de RawProperty |
| `test_superleiloes_parser.py::test_parse_json_api` | JSON mock Superleilões → lista de RawProperty |

### Integração

| Teste | Comportamento |
|-------|---------------|
| `test_api_roi.py::test_post_roi_revenda` | `POST /properties/{id}/roi` retorna 200 com campos `roi_pct`, `payback_months` |
| `test_api_market.py::test_get_market_prices` | `GET /market-prices?city=São Paulo` retorna 200 com dado recente |
| `test_api_radar_index.py::test_granularity_city` | `GET /radar-index?granularity=city` retorna aggregations por município |
| `test_collect_judicial.py::test_job_end_to_end` | Job com mock DataJud → imóvel inserido em `properties` com `source_type=judicial` |

---

## 15. Dependências Python Novas

```toml
# pyproject.toml — adicionar em [project.optional-dependencies.job]
# Nenhuma nova dependência obrigatória — FipeZap usa httpx (já presente)
# Playwright já presente como dep opcional
# Adicionar apenas se FipeZap precisar de parsing Excel:
# openpyxl (já presente)
```

---

## Agent Assignment Rationale

| Agente | Arquivos | Motivo |
|--------|---------|--------|
| `@python-developer` | Todos os `.py` novos | Padrões do projeto (dataclasses, type hints, structlog) |
| `@python-reviewer` | Revisão pós-build | Validar conformidade com interface BankConnector |
| `@database-reviewer` | Migration 012 | Schema e índices |
| `@typescript-reviewer` | Componentes React novos | Type safety + acessibilidade |
| `@gcp-data-architect` | Terraform changes | Cloud Run Jobs + Schedulers |
| `@ai-prompt-specialist-gcp` | Template alerta 2ª praça | Mensagem impactante e clara |
