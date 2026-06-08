# DESIGN: Fase 3 — Todos os Bancos Públicos

> Arquitetura técnica para a Fase 3 do Radar Imóvel: um connector por banco público brasileiro (BB, BRB, BNB, BASA, Banrisul, Banestes), todos seguindo a interface `BankConnector` já consolidada na Caixa, executados por um **job genérico** `collect_bank.py` selecionado por `BANK` env var.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FASE3_TODOS_BANCOS |
| **Date** | 2026-06-08 |
| **Author** | design-agent |
| **DEFINE** | DEFINE_FASE3_TODOS_BANCOS.md (em geração paralela) |
| **BRAINSTORM** | BRAINSTORM_FASE3_TODOS_BANCOS.md (em geração paralela) |
| **Baseia-se em** | [DESIGN_MVP_FASE1_CAIXA.md](./DESIGN_MVP_FASE1_CAIXA.md) |
| **Status** | Ready for Build |

> **Nota de confiança (design-agent):** confiança 0.85 — padrões do projeto (interface `BankConnector`, pipeline de coleta, infra Terraform) totalmente conhecidos e reaproveitados a partir da Fase 1. As URLs e estruturas HTML/PDF de cada banco são **hipóteses iniciais** a validar no `/build` (cada banco expõe um `discover_sources()` configurável). Onde há incerteza de formato, o design isola a lógica volátil em constantes no topo de cada `collector.py`.

---

## Architecture Overview

A Fase 3 **não introduz novos serviços** — reusa todo o pipeline da Fase 1 (Cloud Storage raw, dedup, change detector, score, Pub/Sub `property-events`, alert agent). A única mudança estrutural é trocar `collect_caixa.py` (hardcoded para Caixa) por um **job genérico** `collect_bank.py` que resolve o connector via **registry** a partir da env var `BANK`.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                     RADAR IMÓVEL — FASE 3 (TODOS OS BANCOS)                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Cloud Scheduler (1 conjunto de cron jobs POR BANCO)                  │   │
│  │   collect-caixa-*   collect-bb-*   collect-brb-*   collect-bnb-*      │   │
│  │   collect-basa-*    collect-banrisul-*   collect-banestes-*           │   │
│  └─────────────────────────────────┬────────────────────────────────────┘   │
│                                     │ pubsub_target: {bank, ufs?}             │
│                                     ▼                                         │
│                          ┌────────────────────┐                              │
│                          │  Pub/Sub            │                              │
│                          │  collect-trigger    │  (reuso — sem mudança)       │
│                          └─────────┬──────────┘                              │
│                                     │                                         │
│         ┌───────────────────────────┼──────────────────────────────┐        │
│         ▼  (1 execução de job por banco; env BANK seleciona connector)        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Cloud Run Job  radar-collect-bank   (GENÉRICO)                       │   │
│  │  command: ["python","-m","jobs.collect_bank"]                         │   │
│  │  env: BANK=bb | brb | bnb | basa | banrisul | banestes | caixa       │   │
│  │                                                                       │   │
│  │   CONNECTOR_REGISTRY[BANK]() ──▶ connector (BankConnector)            │   │
│  │        │                                                              │   │
│  │        ├─ discover_sources() ──▶ [urls/PDFs por UF ou nacional]       │   │
│  │        ├─ fetch_raw(url)     ──▶ bytes (HTML / CSV / PDF)             │   │
│  │        │        └──▶ Cloud Storage raw/{bank}/{scope}/{date}/file     │   │
│  │        ├─ parse(bytes)       ──▶ Iterator[RawProperty]                │   │
│  │        └─ normalize(raw)     ──▶ dict (schema Property unificado)     │   │
│  └─────────────────────────────────┬────────────────────────────────────┘   │
│                                     │  (pipeline IDÊNTICO ao da Fase 1)       │
│         ┌───────────────────────────┼───────────────────────────┐           │
│         ▼              ▼             ▼              ▼             ▼           │
│   score_agent   deduplicator  change_detector  Cloud SQL    Pub/Sub          │
│   (reuso)        (reuso)        (reuso)        properties   property-events   │
│                                                    │             │           │
│                                                    └──────┬──────┘           │
│                                                           ▼                  │
│                                          Cloud Run Job  process_alerts       │
│                                          (reuso — Telegram, sem mudança)      │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Componentes (delta sobre Fase 1)

| Componente | Status na Fase 3 | Observação |
|------------|------------------|------------|
| `collect_bank.py` (job genérico) | **Novo** | Substitui `collect_caixa.py`. Lê `BANK` env, resolve connector via registry. |
| `CONNECTOR_REGISTRY` | **Novo** | `dict[str, type[BankConnector]]` em `app/connectors/__init__.py`. |
| Connectors BB/BRB/BNB/BASA/Banrisul/Banestes | **Novo** | 6 módulos seguindo o padrão da Caixa. |
| `radar-collect-bank` Cloud Run Job | **Novo** | 1 job genérico parametrizado por `BANK`. |
| Cloud Schedulers por banco | **Novo** | 1 grupo de cron por banco habilitado. |
| Pub/Sub `property-events`, `collect-trigger` | Reuso | Sem alteração. |
| `deduplicator`, `change_detector`, `score_agent` | Reuso | Já são bank-agnostic. |
| `process_alerts.py`, Telegram | Reuso | Sem alteração. |
| Schema `properties`, `banks`, `sources` | Reuso | Já suporta `bank_id` e `external_code+bank_id` único. |

---

## Key Decisions

### Decision 1: Job genérico `collect_bank.py` com `BANK` env var (não 1 job Python por banco)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-08 |

**Context:** São 7 bancos (Caixa + 6 novos). Manter um arquivo `collect_xxx.py` por banco duplicaria ~120 linhas de orquestração (upload GCS, dedup, change detection, publish) por banco.

**Choice:** Um único job `jobs/collect_bank.py`. A env var `BANK` seleciona o connector via `CONNECTOR_REGISTRY`. Toda a orquestração (idêntica para todos os bancos) vive uma única vez.

**Rationale:** A interface `BankConnector` já abstrai 100% do que muda entre bancos (discover/fetch/parse/normalize). O pipeline downstream (`score → dedup → change → upsert → publish`) é bank-agnostic — vide `collect_caixa.py` linhas 65-122, nada ali é específico da Caixa exceto a instância do connector e o nome do bucket path. Job genérico = DRY + isolamento mantido (cada execução de Cloud Run Job é um processo isolado, falha de um banco não afeta outro).

**Alternatives Rejected:**
1. **1 job Python por banco** — duplicação massiva da orquestração; bug fix exige tocar 7 arquivos.
2. **1 monojob que itera todos os bancos numa execução** — perde isolamento de falha e timeout; um banco lento bloqueia os demais; sem retry granular.

**Consequences:**
- `collect_caixa.py` é **substituído** por `collect_bank.py` (Caixa entra no registry como mais um banco).
- Terraform usa **1** Cloud Run Job (`radar-collect-bank`); cada Scheduler dispara a mesma imagem com `--update-env-vars BANK=<banco>` (ou via `overrides` no `gcloud run jobs execute`).
- `detail_scraper` da Caixa permanece específico e é invocado condicionalmente (apenas quando `BANK=caixa` e o connector o expõe).

### Decision 2: Connector Registry em `app/connectors/__init__.py`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-08 |

**Choice:** Um `dict` mapeando `bank_code → classe do connector`, com função `get_connector(bank_code, **kwargs)`.

**Rationale:** Resolução central, testável, sem `if/elif` espalhado. Permite habilitar/desabilitar bancos só pela tabela `banks.active` + presença no registry.

```python
# app/connectors/__init__.py
from app.connectors.base import BankConnector
from app.connectors.caixa import CaixaConnector
from app.connectors.bb import BBConnector
from app.connectors.brb import BRBConnector
from app.connectors.bnb import BNBConnector
from app.connectors.basa import BASAConnector
from app.connectors.banrisul import BanrisulConnector
from app.connectors.banestes import BanestesConnector

CONNECTOR_REGISTRY: dict[str, type[BankConnector]] = {
    "caixa": CaixaConnector,
    "bb": BBConnector,
    "brb": BRBConnector,
    "bnb": BNBConnector,
    "basa": BASAConnector,
    "banrisul": BanrisulConnector,
    "banestes": BanestesConnector,
}


def get_connector(bank_code: str, **kwargs) -> BankConnector:
    code = bank_code.lower().strip()
    if code not in CONNECTOR_REGISTRY:
        raise ValueError(f"Connector não registrado para banco '{code}'")
    return CONNECTOR_REGISTRY[code](**kwargs)
```

### Decision 3: `requests`/`httpx` + BeautifulSoup como padrão; Playwright só onde houver challenge

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-08 |

**Choice:** Todos os 6 novos bancos começam com `httpx` + BeautifulSoup (HTML) ou `pandas`/`pdfplumber` (CSV/PDF). Playwright fica reservado, como na Caixa, para sites com proteção anti-bot (Radware/Cloudflare).

**Rationale:** A Caixa só precisou de Playwright por causa do Radware Bot Manager. Os demais bancos publicam páginas/PDFs estáticos públicos — `httpx` é mais rápido, estável e leve. Cada `collector` mantém o mesmo formato de `fetch_raw()` da Caixa, podendo adicionar fallback Playwright sem mudar a interface.

**Consequences:**
- Adicionar `pdfplumber` ao extra `job` do `pyproject.toml` (BNB, BASA e Banestes têm PDFs de relação/edital).
- Cada `fetch_raw` valida o content-type; se receber HTML de challenge onde esperava CSV/PDF, loga e retorna `b""` (mesmo padrão da Caixa, `collector.py` linhas 107-109).

### Decision 4: Normalização por banco mapeia para o schema `Property` unificado

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-08 |

**Choice:** Cada banco tem seu `normalizer.py` produzindo **exatamente o mesmo dict** que `CaixaNormalizer.normalize()` (mesmas chaves do model `Property`). Funções utilitárias de parsing de valores BR (`_parse_decimal`, `_parse_discount`, `_normalize_occupancy`) são **extraídas** para `app/connectors/normalize_utils.py` e reusadas.

**Rationale:** Evita reimplementar parsing de moeda BR ("106.667,03") em 7 lugares. O downstream (`Property(bank_id=bank.id, **normalized)` em `collect_caixa.py` linha 78) exige um dict com as chaves do model — contrato fixo.

**Consequences:** Refactor leve: mover os helpers de `caixa/normalizer.py` para `normalize_utils.py` e importar. Caixa passa a importar de lá (mudança retrocompatível, sem alterar comportamento).

### Decision 5: Habilitar bancos via migration `005_update_banks.py`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-08 |

**Context:** `003_seed_banks.py` já inseriu os 7 bancos, todos os novos com `active=False`. O scheduler/registry só deve disparar bancos com connector pronto e validado.

**Choice:** Migration `005_update_banks.py` faz `UPDATE banks SET active=True` para os bancos cujos connectors foram implementados e validados nesta fase. Bancos ainda não validados permanecem `active=False`.

**Rationale:** Liga/desliga de coleta por flag de banco, sem deploy de código. O job genérico verifica `bank.active` antes de coletar (defensivo).

---

## File Manifest

### Connectors — Python (`app/connectors/`)

Cada banco segue **o mesmo conjunto de 4 arquivos** do padrão Caixa (`__init__`, `collector`, `parser`, `normalizer`).

| # | Arquivo | Action | Propósito | Agente | Deps |
|---|---------|--------|-----------|--------|------|
| 1 | `app/connectors/normalize_utils.py` | Create | Helpers de parsing BR extraídos da Caixa (`parse_decimal`, `parse_discount`, `normalize_occupancy`, `extract_type`) | @python-developer | — |
| 2 | `app/connectors/caixa/normalizer.py` | Edit | Importar helpers de `normalize_utils` (refactor retrocompatível) | @python-developer | 1 |
| 3 | `app/connectors/__init__.py` | Edit | `CONNECTOR_REGISTRY` + `get_connector()` | @python-developer | 5-28 |
| 4 | `app/connectors/base.py` | Keep | Interface `BankConnector` (sem mudança) | — | — |
| **BB** | | | | | |
| 5 | `app/connectors/bb/__init__.py` | Create | Export `BBConnector` | @python-developer | 6 |
| 6 | `app/connectors/bb/collector.py` | Create | `BBConnector` — portal + parceiros autorizados | @python-developer | 4, 7, 8 |
| 7 | `app/connectors/bb/parser.py` | Create | Parse HTML/CSV do portal BB → RawProperty | @python-developer | 4 |
| 8 | `app/connectors/bb/normalizer.py` | Create | Dict raw BB → schema Property | @python-developer | 1 |
| **BRB** | | | | | |
| 9 | `app/connectors/brb/__init__.py` | Create | Export `BRBConnector` | @python-developer | 10 |
| 10 | `app/connectors/brb/collector.py` | Create | `BRBConnector` — página oficial + Feirão BRB (Resale) | @python-developer | 4, 11, 12 |
| 11 | `app/connectors/brb/parser.py` | Create | Parse HTML BRB + Resale → RawProperty | @python-developer | 4 |
| 12 | `app/connectors/brb/normalizer.py` | Create | Dict raw BRB → schema Property | @python-developer | 1 |
| **BNB** | | | | | |
| 13 | `app/connectors/bnb/__init__.py` | Create | Export `BNBConnector` | @python-developer | 14 |
| 14 | `app/connectors/bnb/collector.py` | Create | `BNBConnector` — "Bens à Venda" + PDF de relação | @python-developer | 4, 15, 16 |
| 15 | `app/connectors/bnb/parser.py` | Create | Parse HTML + PDF (pdfplumber) BNB → RawProperty | @python-developer | 4 |
| 16 | `app/connectors/bnb/normalizer.py` | Create | Dict raw BNB → schema Property | @python-developer | 1 |
| **BASA** | | | | | |
| 17 | `app/connectors/basa/__init__.py` | Create | Export `BASAConnector` | @python-developer | 18 |
| 18 | `app/connectors/basa/collector.py` | Create | `BASAConnector` — editais de venda + leilão público | @python-developer | 4, 19, 20 |
| 19 | `app/connectors/basa/parser.py` | Create | Parse HTML lista + PDF edital BASA → RawProperty | @python-developer | 4 |
| 20 | `app/connectors/basa/normalizer.py` | Create | Dict raw BASA → schema Property | @python-developer | 1 |
| **Banrisul** | | | | | |
| 21 | `app/connectors/banrisul/__init__.py` | Create | Export `BanrisulConnector` | @python-developer | 22 |
| 22 | `app/connectors/banrisul/collector.py` | Create | `BanrisulConnector` — página de bens à venda | @python-developer | 4, 23, 24 |
| 23 | `app/connectors/banrisul/parser.py` | Create | Parse HTML Banrisul → RawProperty | @python-developer | 4 |
| 24 | `app/connectors/banrisul/normalizer.py` | Create | Dict raw Banrisul → schema Property | @python-developer | 1 |
| **Banestes** | | | | | |
| 25 | `app/connectors/banestes/__init__.py` | Create | Export `BanestesConnector` | @python-developer | 26 |
| 26 | `app/connectors/banestes/collector.py` | Create | `BanestesConnector` — publicações legais + editais PDF | @python-developer | 4, 27, 28 |
| 27 | `app/connectors/banestes/parser.py` | Create | Parse HTML + PDF edital Banestes → RawProperty | @python-developer | 4 |
| 28 | `app/connectors/banestes/normalizer.py` | Create | Dict raw Banestes → schema Property | @python-developer | 1 |

### Jobs — Python (`jobs/`)

| # | Arquivo | Action | Propósito | Agente | Deps |
|---|---------|--------|-----------|--------|------|
| 29 | `jobs/collect_bank.py` | Create | Job genérico: lê `BANK` env, resolve connector via registry, roda pipeline | @python-developer | 3 |
| 30 | `jobs/collect_caixa.py` | Delete (deprecate) | Substituído por `collect_bank.py` com `BANK=caixa` | @python-developer | 29 |

> `collect_caixa.py` é mantido como thin-shim opcional (`os.environ["BANK"]="caixa"; from jobs.collect_bank import main; main()`) durante 1 sprint para não quebrar schedulers existentes, depois removido.

### Migrations — Alembic

| # | Arquivo | Action | Propósito | Agente | Deps |
|---|---------|--------|-----------|--------|------|
| 31 | `migrations/versions/005_update_banks.py` | Create | `UPDATE banks SET active=True` para bancos com connector validado; opcional seed em `sources` | @python-developer | — |

### Infra — Terraform (`infra/terraform/`)

| # | Arquivo | Action | Propósito | Agente | Deps |
|---|---------|--------|-----------|--------|------|
| 32 | `infra/terraform/cloud_run.tf` | Edit | Substituir job `collect_caixa` por `collect_bank` genérico (env `BANK` default vazio; setado por execução) | @gcp-data-architect | — |
| 33 | `infra/terraform/scheduler.tf` | Edit | Refatorar para `for_each` sobre `local.banks` (mapa banco→cron→scope); 1 grupo de schedulers por banco habilitado | @gcp-data-architect | 32 |

### Testes — pytest (`tests/`)

| # | Arquivo | Action | Propósito | Agente | Deps |
|---|---------|--------|-----------|--------|------|
| 34 | `tests/fixtures/banks/bb_list.html` | Create | Fixture HTML do portal BB (3 imóveis) | @python-reviewer | — |
| 35 | `tests/fixtures/banks/brb_list.html` | Create | Fixture HTML BRB + Resale | @python-reviewer | — |
| 36 | `tests/fixtures/banks/bnb_list.html` + `bnb_relacao.pdf` | Create | Fixture HTML "Bens à Venda" + PDF relação BNB | @python-reviewer | — |
| 37 | `tests/fixtures/banks/basa_edital.pdf` + `basa_list.html` | Create | Fixture lista HTML + PDF edital BASA | @python-reviewer | — |
| 38 | `tests/fixtures/banks/banrisul_list.html` | Create | Fixture HTML Banrisul | @python-reviewer | — |
| 39 | `tests/fixtures/banks/banestes_edital.pdf` + `banestes_list.html` | Create | Fixture HTML + PDF edital Banestes | @python-reviewer | — |
| 40 | `tests/unit/connectors/test_bb_parser.py` | Create | Unit: parser + normalizer BB | @python-reviewer | 6,7,8,34 |
| 41 | `tests/unit/connectors/test_brb_parser.py` | Create | Unit: parser + normalizer BRB | @python-reviewer | 10,11,12,35 |
| 42 | `tests/unit/connectors/test_bnb_parser.py` | Create | Unit: parser HTML+PDF + normalizer BNB | @python-reviewer | 14,15,16,36 |
| 43 | `tests/unit/connectors/test_basa_parser.py` | Create | Unit: parser HTML+PDF + normalizer BASA | @python-reviewer | 18,19,20,37 |
| 44 | `tests/unit/connectors/test_banrisul_parser.py` | Create | Unit: parser + normalizer Banrisul | @python-reviewer | 22,23,24,38 |
| 45 | `tests/unit/connectors/test_banestes_parser.py` | Create | Unit: parser HTML+PDF + normalizer Banestes | @python-reviewer | 26,27,28,39 |
| 46 | `tests/unit/connectors/test_registry.py` | Create | Unit: `get_connector()` resolve cada banco; erro em banco inválido | @python-reviewer | 3 |
| 47 | `tests/unit/connectors/test_normalize_utils.py` | Create | Unit: helpers de parsing BR compartilhados | @python-reviewer | 1 |
| 48 | `tests/integration/test_collect_bank.py` | Create | Integration: `collect_bank` com connector fake mockado (fetch/parse), valida upsert + publish | @python-reviewer | 29 |

### Dependências

| # | Arquivo | Action | Propósito | Agente | Deps |
|---|---------|--------|-----------|--------|------|
| 49 | `pyproject.toml` | Edit | Adicionar `pdfplumber>=0.11` ao extra `job` (BNB/BASA/Banestes PDFs) | @python-developer | — |

**Total de Arquivos: 49** (28 connectors/registry, 2 jobs, 1 migration, 2 terraform, 15 testes+fixtures, 1 deps)

---

## Interface de cada Connector

Todos implementam `BankConnector` (discover_sources / fetch_raw / parse / normalize). URLs e estratégias abaixo são **hipóteses a validar no build** — isoladas em constantes no topo de cada `collector.py`.

### Padrão comum de `fetch_raw` (httpx)

```python
# Reutilizado em BB, BRB, BNB, BASA, Banrisul, Banestes
import httpx
from app.core.logging import logger

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
}

def fetch_raw(self, source_url: str) -> bytes:
    try:
        with httpx.Client(headers=_HEADERS, timeout=30, follow_redirects=True) as c:
            r = c.get(source_url)
            r.raise_for_status()
            return r.content
    except Exception as exc:
        logger.error(f"{self.bank_code}.fetch_failed", url=source_url, error=str(exc))
        return b""
```

### 1. Banco do Brasil (`bb`)

| Método | Estratégia |
|--------|-----------|
| `discover_sources()` | Lista de URLs do portal de imóveis BB (`https://www21.bb.com.br/portalbb/imoveis/...`) + parceiros autorizados. Paginação por UF/página se houver. |
| `fetch_raw(url)` | `httpx` GET (padrão). Fallback Playwright se portal exigir JS. |
| `parse(bytes)` | BeautifulSoup sobre os cards de imóvel (`div.imovel`/tabela). Extrai código, endereço, valores, link. `yield RawProperty(bank_code="bb", ...)`. |
| `normalize(raw)` | `external_code`, `city`, `state`, `current_value`, `appraisal_value`, `discount_percent`, `official_url`, `property_type` (de título), `occupancy_status` ("Não informado" se ausente). |

### 2. BRB (`brb`)

| Método | Estratégia |
|--------|-----------|
| `discover_sources()` | 2 fontes: página oficial de imóveis BRB + Feirão BRB / **Resale** (`https://brb.resale.com.br/...`). Retorna ambas URLs. |
| `fetch_raw(url)` | `httpx` GET. Resale pode expor JSON de API — `fetch_raw` lida com ambos (HTML e JSON). |
| `parse(bytes, url)` | Detecta fonte pela URL: se Resale → parse JSON/listagem; se oficial → BeautifulSoup. `source_name` distingue (`brb_oficial` vs `brb_resale`). |
| `normalize(raw)` | Mesmo schema. `sale_modality` = "Venda direta" (Resale) ou conforme página. |

### 3. Banco do Nordeste (`bnb`)

| Método | Estratégia |
|--------|-----------|
| `discover_sources()` | Página "Bens à Venda" (HTML) + URL do **PDF de relação** de imóveis. Retorna lista com ambos. |
| `fetch_raw(url)` | `httpx` GET; detecta content-type (`application/pdf` vs `text/html`). |
| `parse(bytes, url)` | Se PDF → `pdfplumber` extrai tabela de imóveis; se HTML → BeautifulSoup. Normaliza linhas em RawProperty. |
| `normalize(raw)` | Mapeia colunas do PDF (município, descrição, valor, área) ao schema. `state` derivado da UF do imóvel ou município. |

### 4. Banco da Amazônia (`basa`)

| Método | Estratégia |
|--------|-----------|
| `discover_sources()` | Página de editais de venda de bens (HTML) → coleta links de **editais PDF** (leilão/praça pública). Retorna lista de PDFs + a página índice. |
| `fetch_raw(url)` | `httpx` GET PDF/HTML. |
| `parse(bytes, url)` | HTML índice → lista de editais (metadados: nº edital, data leilão). PDF edital → `pdfplumber` extrai lotes de imóveis. Cada lote = RawProperty com `edital_number`, `auction_date`. |
| `normalize(raw)` | Schema + `edital_number`, `auction_date`, `sale_modality="Leilão"`. `edital_url` preenchido (alimenta Fase 2 de IA). |

### 5. Banrisul (`banrisul`)

| Método | Estratégia |
|--------|-----------|
| `discover_sources()` | Página de bens à venda Banrisul (lançada abr/2026) — 1 ou mais URLs de listagem (possível paginação). |
| `fetch_raw(url)` | `httpx` GET HTML. |
| `parse(bytes)` | BeautifulSoup sobre cards/tabela. |
| `normalize(raw)` | Schema padrão; `state` default "RS" se não houver (banco gaúcho), mas respeita UF do imóvel quando presente. |

### 6. Banestes (`banestes`)

| Método | Estratégia |
|--------|-----------|
| `discover_sources()` | Página de publicações legais / editais de alienação → links de **editais PDF**. |
| `fetch_raw(url)` | `httpx` GET HTML/PDF. |
| `parse(bytes, url)` | HTML índice → links de editais; PDF → `pdfplumber` extrai imóveis. `edital_number` + `auction_date` quando presentes. |
| `normalize(raw)` | Schema padrão; `state` default "ES", `sale_modality` conforme edital, `edital_url` preenchido. |

---

## Schema de Normalização (unificado)

Todos os normalizers produzem um dict com as chaves do model `Property` (`app/models/property.py`). Campos não disponíveis em um banco → `None` (nullable) ou default seguro. Tabela de mapeamento campo-fonte por banco:

| Campo `Property` | Caixa (ref) | BB | BRB | BNB | BASA | Banrisul | Banestes |
|------------------|-------------|----|-----|-----|------|----------|----------|
| `external_code` ⚑ | N° do imóvel | código portal | código/Resale id | item da relação | nº lote/edital | código listagem | item edital |
| `bank_code` | "caixa" | "bb" | "brb" | "bnb" | "basa" | "banrisul" | "banestes" |
| `title` | Descrição | título card | título | descrição | descrição lote | título | descrição |
| `property_type` ⚑ | de título | de título | de título | de descrição | de descrição | de título | de descrição |
| `address` | Endereço | endereço | endereço | endereço/município | endereço lote | endereço | endereço |
| `neighborhood` | Bairro | bairro | bairro | — | — | bairro | — |
| `city` ⚑ | Cidade | cidade | cidade | município | município | cidade | município |
| `state` ⚑ | UF | UF | "DF" (default) | UF | UF (Norte) | "RS" (default) | "ES" (default) |
| `appraisal_value` | Valor avaliação | avaliação | avaliação | valor avaliação | avaliação edital | avaliação | avaliação |
| `minimum_value` ⚑ | Preço | preço/lance mín | preço | valor mín | lance mínimo | preço | lance mínimo |
| `current_value` ⚑ | Preço | preço | preço | valor | valor atual | preço | valor |
| `discount_percent` | Desconto/calc | calc | calc | calc | calc | calc | calc |
| `occupancy_status` ⚑ | Situação | "Não informado" | "Não informado" | "Não informado" | edital | "Não informado" | edital |
| `sale_modality` ⚑ | Modalidade | "Venda direta" | "Venda direta"/Resale | "Venda direta" | "Leilão" | "Venda direta" | edital |
| `edital_number` | — | — | — | — | nº edital | — | nº edital |
| `auction_date` | detalhe | — | — | — | data leilão | — | data leilão |
| `edital_url` | detalhe | — | — | PDF relação | PDF edital | — | PDF edital |
| `official_url` ⚑ | Link de acesso | link card | link/Resale | link/PDF | link edital | link | link/PDF |
| `status` ⚑ | "active" | "active" | "active" | "active" | "active" | "active" | "active" |

⚑ = campo `NOT NULL` no model (deve sempre ter valor; defaults aplicados se ausente: `current_value`/`minimum_value` → `Decimal("0")`, `occupancy_status`/`sale_modality` → "Não informado"/conforme banco).

**Regra de desconto (reuso):** se `discount_percent` não vier explícito e houver `appraisal_value > 0`, calcula `((appraisal - current) / appraisal * 100)` — idêntico a `CaixaNormalizer` linha 61-62.

**Parsing de moeda BR (reuso):** `normalize_utils.parse_decimal("106.667,03") → Decimal("106667.03")` — extraído da Caixa.

---

## Terraform

### Cloud Run Job genérico (`cloud_run.tf` — Edit)

```hcl
# Substitui google_cloud_run_v2_job.collect_caixa
resource "google_cloud_run_v2_job" "collect_bank" {
  name     = "radar-collect-bank"
  location = var.region

  template {
    template {
      service_account = google_service_account.job_sa.email
      max_retries     = 1
      timeout         = "3600s"
      containers {
        image   = local.placeholder
        command = ["python", "-m", "jobs.collect_bank"]
        # BANK é injetado por execução (override) — ver scheduler.tf
        env {
          name  = "BANK"
          value = "" # default vazio; cada execução faz override
        }
      }
    }
  }

  lifecycle { ignore_changes = [template] }
  depends_on = [google_project_service.apis]
}
```

### Schedulers por banco (`scheduler.tf` — Edit)

```hcl
locals {
  # Bancos habilitados na Fase 3 (espelha banks.active=True)
  banks = {
    caixa    = { ufs = local.ufs }   # mantém comportamento atual
    bb       = { ufs = [] }          # nacional, sem split por UF
    brb      = { ufs = [] }
    bnb      = { ufs = [] }
    basa     = { ufs = [] }
    banrisul = { ufs = [] }
    banestes = { ufs = [] }
  }
  collect_schedules = ["0 11 * * *", "0 17 * * *", "0 23 * * *"] # 08h/14h/20h BRT
}

# Produto cartesiano banco × horário
resource "google_cloud_scheduler_job" "collect" {
  for_each = {
    for pair in setproduct(keys(local.banks), local.collect_schedules) :
    "${pair[0]}-${replace(pair[1], " ", "-")}" => { bank = pair[0], cron = pair[1] }
  }

  name      = "collect-${each.value.bank}-${replace(each.value.cron, " ", "-")}"
  schedule  = each.value.cron
  time_zone = "UTC"

  pubsub_target {
    topic_name = google_pubsub_topic.collect_trigger.id
    data = base64encode(jsonencode({
      bank = each.value.bank
      ufs  = local.banks[each.value.bank].ufs
    }))
  }
}
```

> **Acionamento do job:** o subscriber de `collect-trigger` (ou um Cloud Function/Eventarc trigger) executa `gcloud run jobs execute radar-collect-bank --update-env-vars BANK=<bank>` por mensagem. Alternativa simples para MVP: Cloud Scheduler com `http_target` chamando a API `jobs.run` do Cloud Run Admin com `overrides.containerOverrides[].env BANK=<bank>` diretamente, eliminando o passo Pub/Sub. **Decisão: manter Pub/Sub `collect-trigger` (reuso Fase 1) + thin trigger que faz `jobs execute` com override de `BANK`.**

---

## Test Plan

| Tipo | Escopo | Arquivos | Ferramentas | Meta |
|------|--------|----------|-------------|------|
| Unit (parser/normalizer) | 1 suite por banco: parse de fixture HTML/PDF/CSV → N RawProperty corretos; normalize → dict com chaves do schema e valores BR corretos | `tests/unit/connectors/test_{bank}_parser.py` | pytest + fixtures locais | parse retorna ≥3 imóveis; valores decimais corretos; campos NOT NULL preenchidos |
| Unit (registry) | `get_connector("bb")` → BBConnector; banco inválido → ValueError | `test_registry.py` | pytest | 7 bancos resolvem; erro em desconhecido |
| Unit (utils) | `parse_decimal`, `parse_discount`, `normalize_occupancy`, `extract_type` | `test_normalize_utils.py` | pytest | casos BR (milhar/decimal), nulos, percentuais |
| Integration | `collect_bank.run()` com connector fake (fetch/parse mockados) → valida upload GCS mock, dedup, change detection, publish | `test_collect_bank.py` | pytest + `responses`/monkeypatch + GCS/Pub-Sub mock | pipeline executa fim-a-fim sem rede real; novos e changed contabilizados |

**Fixtures (offline, sem rede):**
- `tests/fixtures/banks/{bank}_list.html` — HTML real salvo (snapshot) com ≥3 imóveis por banco.
- `tests/fixtures/banks/{bnb_relacao,basa_edital,banestes_edital}.pdf` — PDFs reais reduzidos (1-2 páginas) para validar extração `pdfplumber`.
- Mock de `httpx`/`fetch_raw`: retorna bytes da fixture; nenhum teste acessa internet.
- `collect_bank` integration: `monkeypatch` em `storage.Client`, `pubsub_v1.PublisherClient` e `SessionLocal` (DB de teste igual ao `conftest.py` da Fase 1).

**Padrão de teste de parser (espelha `test_caixa_parser.py`):**
```python
def test_bb_parser_extracts_properties():
    raw = (FIXTURES / "banks" / "bb_list.html").read_bytes()
    props = list(BBConnector().parse(raw, "https://bb-portal/lista"))
    assert len(props) >= 3
    p = props[0]
    assert p.bank_code == "bb"
    assert p.external_code
    norm = BBConnector().normalize(p)
    assert norm["bank_code"] == "bb"
    assert norm["state"] and len(norm["state"]) == 2
    assert isinstance(norm["current_value"], Decimal)
```

---

## Error Handling (delta sobre Fase 1)

| Erro | Estratégia | Retry? |
|------|-----------|--------|
| Banco retorna HTML de challenge onde esperava CSV/PDF | `fetch_raw` detecta content-type, loga `{bank}.fetch_got_html`, retorna `b""`, pula source | Próxima execução agendada |
| PDF malformado (pdfplumber falha) | Loga `{bank}.pdf_parse_failed` com URL, salva raw em GCS para diagnóstico, continua | Não |
| `BANK` env ausente/inválido | `collect_bank` loga erro e `sys.exit(1)` (igual `collect_caixa` com UF) | Não |
| Banco `active=False` mas disparado | `collect_bank` loga warning e encerra sem coletar | Não |
| Layout HTML mudou (0 imóveis extraídos) | Data Quality Gate "imóveis > 0" dispara alerta admin (possível mudança de formato) | Não |

---

## Configuration (delta)

| Config Key | Tipo | Default | Descrição |
|------------|------|---------|-----------|
| `BANK` | string | — | Banco a coletar (caixa/bb/brb/bnb/basa/banrisul/banestes) — seleciona connector |
| `FETCH_DETAIL` | bool | `true` | Só aplicável a `caixa` (detail_scraper); ignorado pelos demais |
| `{BANK}_REQUEST_DELAY_MS` | int | `1000` | Delay entre requisições por banco (respeito a servidores públicos) |

---

## Quality Gate (pré-build)

```text
PRE-FLIGHT CHECK
├─ [x] Padrões carregados da Fase 1 (BankConnector, pipeline collect, Terraform)
├─ [x] Diagrama de arquitetura ASCII (job genérico + registry)
├─ [x] Decisões com rationale (job genérico, registry, httpx-first, normalize unificado, migration)
├─ [x] File manifest completo (49 arquivos, todos os 6 bancos × 4 arquivos + registry + job + infra + testes)
├─ [x] Agente atribuído a cada arquivo (@python-developer / @gcp-data-architect / @python-reviewer)
├─ [x] Interface concreta por banco (discover/fetch/parse/normalize + URLs e estratégia)
├─ [x] Schema de normalização unificado (tabela de mapeamento por banco)
├─ [x] Test plan com fixtures HTML/PDF/CSV e mocks por banco
├─ [x] Unidades deployáveis self-contained (1 job genérico, connectors isolados por banco)
└─ [x] Sem dependências compartilhadas que quebrem isolamento de execução
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-08 | design-agent | Versão inicial — Fase 3: 6 connectors novos (BB, BRB, BNB, BASA, Banrisul, Banestes), job genérico `collect_bank.py`, registry, normalize_utils, migration 005, Terraform refatorado, 49 arquivos |

---

## Next Step

**Status: Ready for Build**

**Ready for:** `/build .claude/sdd/features/DESIGN_FASE3_TODOS_BANCOS.md`

> Ao iniciar o build, **validar primeiro** as URLs e estruturas reais de cada banco (são hipóteses neste design) e ajustar as constantes no topo de cada `collector.py`/`parser.py`. Recomenda-se implementar e validar **um banco por vez** (sugestão de ordem por simplicidade esperada: BB → Banrisul → BNB → BRB → BASA → Banestes), habilitando cada um em `banks.active` (migration 005) só após os testes passarem.
