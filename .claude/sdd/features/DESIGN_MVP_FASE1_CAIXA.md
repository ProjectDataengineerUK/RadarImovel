# DESIGN: MVP Fase 1 — Radar Imóvel (Caixa)

> Arquitetura técnica completa para o MVP: coleta automatizada da Caixa, detecção de mudanças, alertas Telegram e painel web SaaS no GCP.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | MVP_FASE1_CAIXA |
| **Date** | 2026-05-26 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_MVP_FASE1_CAIXA.md](./DEFINE_MVP_FASE1_CAIXA.md) |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                        RADAR IMÓVEL — MVP FASE 1                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────────────────┐     │
│  │   Cloud      │───▶│   Pub/Sub   │───▶│  Cloud Run Job           │     │
│  │  Scheduler   │    │  collect-   │    │  collect_caixa.py        │     │
│  │  (3x/dia)    │    │  trigger    │    │  (1 job por UF)          │     │
│  └─────────────┘    └─────────────┘    └──────────┬───────────────┘     │
│                                                    │                     │
│                          ┌─────────────────────────▼──────────┐         │
│                          │         Cloud Storage               │         │
│                          │  raw/caixa/{uf}/{date}/arquivo.xlsx │         │
│                          └─────────────────────────┬──────────┘         │
│                                                    │                     │
│                          ┌─────────────────────────▼──────────┐         │
│                          │   Parser → Normalizador → Dedup     │         │
│                          │   (dentro do Cloud Run Job)         │         │
│                          └─────────────────────────┬──────────┘         │
│                                                    │                     │
│                          ┌─────────────────────────▼──────────┐         │
│                          │   Cloud SQL PostgreSQL + PostGIS     │         │
│                          │   properties, property_changes,      │         │
│                          │   users, watchlists, alerts          │         │
│                          └────────┬────────────────┬──────────┘         │
│                                   │                │                     │
│            ┌──────────────────────▼──┐   ┌────────▼─────────────┐      │
│            │  Pub/Sub                │   │  FastAPI Cloud Run     │      │
│            │  property-events        │   │  API Backend           │      │
│            └──────────────────────┬─┘   └────────┬─────────────┘      │
│                                   │               │                     │
│            ┌──────────────────────▼──┐   ┌────────▼─────────────┐      │
│            │  Cloud Run Job          │   │  Firebase Hosting      │      │
│            │  alert_agent.py         │   │  Next.js Dashboard     │      │
│            └──────────────────────┬─┘   └────────┬─────────────┘      │
│                                   │               │                     │
│                          ┌────────▼──┐   ┌────────▼─────────────┐      │
│                          │  Telegram  │   │  Firebase Auth         │      │
│                          │  Bot API   │   │  (JWT)                 │      │
│                          └────────────┘   └──────────────────────┘      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Componente | Propósito | Tecnologia |
|------------|-----------|------------|
| Cloud Scheduler | Dispara coleta 3x/dia | GCP Cloud Scheduler |
| Pub/Sub `collect-trigger` | Enfileira tarefas de coleta por UF | GCP Pub/Sub |
| Cloud Run Job `collect_caixa` | Coleta, parseia, normaliza, detecta mudanças | Python, Playwright/requests, BeautifulSoup |
| Cloud Storage `radar-raw` | Armazena arquivos brutos (evidência + replay) | GCP Cloud Storage |
| Cloud SQL PostgreSQL + PostGIS | Dados estruturados de imóveis, usuários, alertas | PostgreSQL 15 + PostGIS 3 |
| Pub/Sub `property-events` | Eventos de novos imóveis e mudanças detectadas | GCP Pub/Sub |
| Cloud Run Job `alert_agent` | Consome eventos, verifica watchlists, envia alertas | Python, Telegram Bot API |
| FastAPI API | Backend REST para o dashboard | Python, FastAPI, SQLAlchemy |
| Next.js Dashboard | Frontend SaaS com tabela, filtros e detalhe | Next.js 14, TypeScript, Tailwind, shadcn/ui |
| Firebase Auth | Autenticação SaaS multi-tenant | Firebase Authentication |
| Firebase Hosting | Deploy do frontend Next.js (modo static export) | Firebase Hosting |
| Secret Manager | Segredos: DB password, Telegram token, etc. | GCP Secret Manager |
| Cloud Logging | Logs estruturados de todos os serviços | GCP Cloud Logging |

---

## Key Decisions

### Decision 1: Cloud Run Jobs para coletores (não Cloud Functions)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-05-26 |

**Context:** A coleta de imóveis da Caixa por UF pode envolver download de arquivos grandes, múltiplas requisições HTTP com delays e parsing pesado.

**Choice:** Cloud Run Jobs com timeout configurável (até 24h).

**Rationale:** Cloud Functions tem timeout máximo de 9 minutos. Uma UF como SP pode ter milhares de imóveis — 9 minutos não é suficiente para coletar, parsear e processar. Cloud Run Jobs rodam em container, têm timeout longo e são cobrados por execução.

**Alternatives Rejected:**
1. Cloud Functions 2nd gen — timeout de 60min, mas sem controle de concorrência por UF e custo maior em execuções longas
2. Compute Engine sempre ligado — custo fixo, over-engineering para MVP

**Consequences:**
- Cada UF roda como job independente — falha isolada por UF
- Imagem Docker precisa ser mantida para os jobs
- Billing por execução (pay-per-use)

---

### Decision 2: requests + BeautifulSoup primeiro, Playwright como fallback

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-05-26 |

**Context:** Não sabemos ainda se a Caixa usa JavaScript pesado para renderizar as listas ou se são páginas/arquivos estáticos (XLSX/HTML).

**Choice:** Começar com `requests` + `BeautifulSoup`. Adicionar `Playwright` só se a página exigir JavaScript.

**Rationale:** Playwright requer um browser headless, aumenta a imagem Docker em ~300MB e é 10x mais lento. A Caixa disponibiliza listas em formato XLSX por UF — `requests` com download direto é suficiente e muito mais estável.

**Alternatives Rejected:**
1. Playwright desde o início — imagem maior, mais lento, complexidade desnecessária se XLSX funciona
2. Scrapy — overhead de framework, desnecessário para um único conector no MVP

**Consequences:**
- `collector.py` terá método `_try_requests()` com fallback `_try_playwright()` se retorno for vazio/erro
- `Playwright` entra como dependência opcional no `pyproject.toml`

---

### Decision 3: Firebase Auth para autenticação SaaS

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-05-26 |

**Context:** SaaS público com múltiplos usuários, LGPD aplicável, sem tempo para implementar auth customizado seguro.

**Choice:** Firebase Authentication com verificação de JWT no backend FastAPI.

**Rationale:** Firebase Auth resolve e-mail/senha, OAuth social e JWT em horas, com free tier de 10k usuários/mês. O backend verifica o token via `firebase-admin` SDK — sem estado de sessão no servidor.

**Alternatives Rejected:**
1. Auth0 — custo mais alto para MVP
2. Custom JWT com bcrypt — risco de segurança, esforço não-core

**Consequences:**
- Cada requisição à API carrega `Authorization: Bearer <firebase_jwt>`
- Backend usa `firebase-admin` para verificar token e extrair `uid`
- `users.firebase_uid` é a chave de ligação entre Firebase e o banco

---

### Decision 4: Pub/Sub como bus de eventos entre coleta e alertas

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-05-26 |

**Context:** O job de coleta detecta um novo imóvel e precisa acionar o agente de alertas. Chamada direta entre jobs acopla os serviços.

**Choice:** Pub/Sub topic `property-events`. O job de coleta publica o evento; o agente de alertas consome de forma assíncrona.

**Rationale:** Desacoplamento total entre coleta e alertas. Retry automático com DLQ. O agente de alertas pode estar indisponível sem afetar a coleta.

**Alternatives Rejected:**
1. Chamada HTTP direta — acoplamento, sem retry, falha em cascata
2. Redis Queue — infraestrutura adicional, custo extra para MVP

**Consequences:**
- Latência de alerta pode ser de até 30min (aceitável segundo success criteria)
- DLQ para mensagens não processadas após 5 tentativas

---

### Decision 5: Conexão Telegram via token único gerado no dashboard

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-05-26 |

**Context:** Open Question OQ-001 do DEFINE: como o usuário conecta o Telegram.

**Choice:** Dashboard gera token UUID de 8 caracteres. Usuário envia `/start TOKEN` para o bot. Bot salva `telegram_chat_id` na tabela `users`.

**Rationale:** Fluxo simples, sem OAuth, sem redirect. Token expira em 15 minutos. Funciona em qualquer cliente Telegram.

**Alternatives Rejected:**
1. Deep link `tg://resolve?domain=bot&start=TOKEN` — mais elegante, mas depende do cliente Telegram ter suporte
2. QR Code — complexidade extra, mesmo fluxo

**Consequences:**
- Token armazenado em cache (Redis/Memorystore) com TTL de 15 minutos
- Endpoint `POST /users/telegram/token` gera o token
- Webhook do bot recebe `/start TOKEN` e vincula chat_id

---

### Decision 6: Next.js Static Export no Firebase Hosting

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-05-26 |

**Context:** Frontend Next.js precisa de hosting. Opções: Cloud Run (SSR), Firebase Hosting (static), Vercel.

**Choice:** `next export` (static) + Firebase Hosting.

**Rationale:** Para MVP, não precisamos de SSR — dados vêm da API com React Query. Firebase Hosting é CDN global, gratuito no Spark plan até 10GB/mês, e integra com Firebase Auth nativamente.

**Alternatives Rejected:**
1. Cloud Run com Next.js SSR — necessário apenas para SEO ou server components avançados
2. Vercel — vendor fora do GCP, billing separado

**Consequences:**
- Todas as rotas são SPA client-side (React Query + axios)
- `next.config.js` com `output: 'export'`
- API calls sempre via `NEXT_PUBLIC_API_URL`

---

## File Manifest

### Backend — Python

| # | Arquivo | Action | Propósito | Agente | Deps |
|---|---------|--------|-----------|--------|------|
| 1 | `app/core/config.py` | Create | Settings via env vars + Secret Manager | @python-developer | — |
| 2 | `app/core/database.py` | Create | SQLAlchemy engine + sessão Cloud SQL | @python-developer | 1 |
| 3 | `app/core/logging.py` | Create | Logging estruturado JSON para Cloud Logging | @python-developer | 1 |
| 4 | `app/models/base.py` | Create | Base declarativa SQLAlchemy + UUID helper | @python-developer | 2 |
| 5 | `app/models/bank.py` | Create | Models `Bank` e `Source` | @python-developer | 4 |
| 6 | `app/models/property.py` | Create | Models `Property` e `PropertyChange` | @python-developer | 4 |
| 7 | `app/models/user.py` | Create | Models `User`, `Watchlist`, `Alert`, `Favorite` | @python-developer | 4 |
| 8 | `app/models/document.py` | Create | Model `Document` (vazio no MVP, schema pronto) | @python-developer | 4 |
| 9 | `app/connectors/base.py` | Create | Interface abstrata `BankConnector` | @python-developer | — |
| 10 | `app/connectors/caixa/__init__.py` | Create | Export do conector Caixa | @python-developer | 9 |
| 11 | `app/connectors/caixa/collector.py` | Create | Coleta lista por UF (requests + fallback Playwright) | @python-developer | 9, 1 |
| 12 | `app/connectors/caixa/parser.py` | Create | Parsing XLSX/HTML da Caixa → dict raw | @python-developer | — |
| 13 | `app/connectors/caixa/normalizer.py` | Create | Dict raw → schema `Property` padrão | @python-developer | 6 |
| 14 | `app/agents/deduplicator.py` | Create | content_hash SHA-256, verifica duplicata no DB | @python-developer | 6, 2 |
| 15 | `app/agents/change_detector.py` | Create | Compara property com DB, cria `PropertyChange` | @python-developer | 6, 2 |
| 16 | `app/agents/score_agent.py` | Create | Score básico: desconto 0-60pts + ocupação 0-40pts | @python-developer | 6 |
| 17 | `app/agents/alert_agent.py` | Create | Consome Pub/Sub, verifica watchlists, envia Telegram | @python-developer | 7, 18 |
| 18 | `app/services/notification.py` | Create | Camada abstrata `NotificationChannel` + `TelegramChannel` | @python-developer | — |
| 19 | `app/services/telegram.py` | Create | Telegram Bot API (send_message, set_webhook, handle_update) | @python-developer | 1 |
| 20 | `app/services/geocoding.py` | Create | CEP → lat/lng via ViaCEP + Nominatim (gratuito) | @python-developer | 1 |
| 21 | `app/api/main.py` | Create | FastAPI app factory + routers + CORS + middleware | @python-developer | 22-27 |
| 22 | `app/api/middleware/auth.py` | Create | Verificação Firebase JWT → injeta `current_user` | @python-developer | 1 |
| 23 | `app/api/routes/properties.py` | Create | `GET /properties` com filtros, `GET /properties/{id}` | @python-developer | 6, 2 |
| 24 | `app/api/routes/watchlists.py` | Create | CRUD de watchlists do usuário | @python-developer | 7, 2 |
| 25 | `app/api/routes/users.py` | Create | `GET /users/me`, `POST /users/telegram/token` | @python-developer | 7 |
| 26 | `app/api/routes/alerts.py` | Create | `GET /alerts` — histórico de alertas enviados | @python-developer | 7 |
| 27 | `app/api/routes/admin.py` | Create | Status dos jobs, última coleta, erros recentes | @python-developer | 2 |
| 28 | `jobs/collect_caixa.py` | Create | Entry point Cloud Run Job de coleta | @python-developer | 11-16 |
| 29 | `jobs/process_alerts.py` | Create | Entry point Cloud Run Job de alertas (Pub/Sub pull) | @python-developer | 17 |

### Migrations — Alembic

| # | Arquivo | Action | Propósito | Agente | Deps |
|---|---------|--------|-----------|--------|------|
| 30 | `migrations/env.py` | Create | Config Alembic com Cloud SQL | @python-developer | 2 |
| 31 | `migrations/versions/001_initial_schema.py` | Create | Schema completo: todas as tabelas do DEFINE | @python-developer | 4-8 |

### Infra — Terraform

| # | Arquivo | Action | Propósito | Agente | Deps |
|---|---------|--------|-----------|--------|------|
| 32 | `infra/terraform/variables.tf` | Create | project_id, region, db_password, etc. | @gcp-data-architect | — |
| 33 | `infra/terraform/main.tf` | Create | Provider GCP, habilitação de APIs | @gcp-data-architect | 32 |
| 34 | `infra/terraform/cloud_sql.tf` | Create | Cloud SQL PostgreSQL + PostGIS, private IP | @gcp-data-architect | 33 |
| 35 | `infra/terraform/cloud_storage.tf` | Create | Bucket `radar-raw` (arquivos brutos) | @gcp-data-architect | 33 |
| 36 | `infra/terraform/pubsub.tf` | Create | Topics `collect-trigger`, `property-events` + DLQ | @gcp-data-architect | 33 |
| 37 | `infra/terraform/scheduler.tf` | Create | 3 Cloud Scheduler jobs (08h, 14h, 20h) | @gcp-data-architect | 36 |
| 38 | `infra/terraform/cloud_run.tf` | Create | Cloud Run API + Jobs (collect_caixa, alert_agent) | @gcp-data-architect | 33, 34 |
| 39 | `infra/terraform/iam.tf` | Create | Service accounts + IAM mínimo por serviço | @gcp-data-architect | 33 |
| 40 | `infra/terraform/secret_manager.tf` | Create | Secrets: DB_URL, TELEGRAM_TOKEN, FIREBASE_CREDS | @gcp-data-architect | 33 |
| 41 | `infra/terraform/outputs.tf` | Create | Outputs: API URL, DB IP, bucket name | @gcp-data-architect | 32-40 |

### Docker + CI

| # | Arquivo | Action | Propósito | Agente | Deps |
|---|---------|--------|-----------|--------|------|
| 42 | `Dockerfile.api` | Create | Imagem para FastAPI Cloud Run | @python-developer | 21 |
| 43 | `Dockerfile.job` | Create | Imagem para Cloud Run Jobs (collect + alerts) | @python-developer | 28, 29 |
| 44 | `cloudbuild.yaml` | Create | CI/CD: build, push, deploy no GCP | @gcp-data-architect | 42, 43 |
| 45 | `pyproject.toml` | Create | Dependências Python + ruff + pytest | @python-developer | — |
| 46 | `.env.example` | Create | Template de variáveis de ambiente | @python-developer | — |

### Frontend — Next.js

| # | Arquivo | Action | Propósito | Agente | Deps |
|---|---------|--------|-----------|--------|------|
| 47 | `frontend/package.json` | Create | Deps: Next.js, Tailwind, shadcn, TanStack Table, React Query, axios | @typescript-reviewer | — |
| 48 | `frontend/lib/firebase.ts` | Create | Init Firebase Auth | @typescript-reviewer | 47 |
| 49 | `frontend/lib/api.ts` | Create | axios client com Bearer token automático | @typescript-reviewer | 48 |
| 50 | `frontend/lib/types.ts` | Create | Tipos TypeScript: Property, Watchlist, User, Alert | @typescript-reviewer | — |
| 51 | `frontend/hooks/useAuth.ts` | Create | Hook Firebase Auth (login, logout, currentUser) | @typescript-reviewer | 48 |
| 52 | `frontend/hooks/useProperties.ts` | Create | React Query: listagem + filtros + detalhe | @typescript-reviewer | 49 |
| 53 | `frontend/app/layout.tsx` | Create | Root layout + QueryClient + AuthProvider | @typescript-reviewer | 48, 51 |
| 54 | `frontend/app/page.tsx` | Create | Redirect: autenticado → /dashboard, senão → /login | @typescript-reviewer | 51 |
| 55 | `frontend/app/login/page.tsx` | Create | Login / cadastro com Firebase Auth UI | @typescript-reviewer | 51 |
| 56 | `frontend/app/dashboard/page.tsx` | Create | Cards: novos hoje, preço reduziu, leilões próximos | @typescript-reviewer | 52 |
| 57 | `frontend/app/imoveis/page.tsx` | Create | Tabela TanStack Table + filtros (cidade, UF, preço, desconto) | @typescript-reviewer | 52 |
| 58 | `frontend/app/imoveis/[id]/page.tsx` | Create | Detalhe: dados, histórico de mudanças, score, link oficial | @typescript-reviewer | 52 |
| 59 | `frontend/app/alertas/page.tsx` | Create | Criar/editar/remover watchlists | @typescript-reviewer | 49 |
| 60 | `frontend/app/configuracoes/page.tsx` | Create | Conexão Telegram (gera token, instruções) | @typescript-reviewer | 49 |
| 61 | `frontend/app/admin/page.tsx` | Create | Status dos coletores, última coleta, erros | @typescript-reviewer | 49 |
| 62 | `frontend/components/PropertyTable.tsx` | Create | Tabela com TanStack Table, paginação, ordenação | @typescript-reviewer | 50 |
| 63 | `frontend/components/PropertyFilters.tsx` | Create | Sidebar de filtros: banco, UF, cidade, preço, desconto, ocupação | @typescript-reviewer | 50 |
| 64 | `frontend/components/ScoreBadge.tsx` | Create | Badge colorido: 90-100 verde, 70-89 amarelo, <70 vermelho | @typescript-reviewer | 50 |
| 65 | `frontend/components/WatchlistForm.tsx` | Create | Form shadcn para criar/editar watchlist | @typescript-reviewer | 50 |
| 66 | `frontend/components/TelegramConnect.tsx` | Create | Exibe token + instruções + status de vinculação | @typescript-reviewer | 49 |
| 67 | `frontend/next.config.js` | Create | `output: 'export'`, env vars públicas | @typescript-reviewer | — |

### Testes

| # | Arquivo | Action | Propósito | Agente | Deps |
|---|---------|--------|-----------|--------|------|
| 68 | `tests/unit/connectors/test_caixa_parser.py` | Create | Unit tests do parser Caixa com fixtures XLSX/HTML | @python-reviewer | 12 |
| 69 | `tests/unit/agents/test_deduplicator.py` | Create | Unit tests do content_hash e deduplicação | @python-reviewer | 14 |
| 70 | `tests/unit/agents/test_change_detector.py` | Create | Unit tests de detecção de mudança de campos | @python-reviewer | 15 |
| 71 | `tests/unit/agents/test_score_agent.py` | Create | Unit tests do cálculo de score | @python-reviewer | 16 |
| 72 | `tests/integration/test_api_properties.py` | Create | Integration tests dos endpoints de imóveis | @python-reviewer | 23 |
| 73 | `tests/integration/test_alert_agent.py` | Create | Integration tests do agente de alertas com Telegram mock | @python-reviewer | 17 |
| 74 | `tests/conftest.py` | Create | Fixtures: DB de teste, usuário mock, propriedades de exemplo | @python-reviewer | 2, 4-8 |

**Total de Arquivos: 74**

---

## Agent Assignment Rationale

| Agente | Arquivos | Justificativa |
|--------|----------|---------------|
| @python-developer | 1-31, 42-46 | Backend Python, modelos SQLAlchemy, conectores, agentes, FastAPI, Docker |
| @gcp-data-architect | 32-41, 44 | Terraform GCP: Cloud SQL, Cloud Run, Pub/Sub, IAM, Secret Manager |
| @typescript-reviewer | 47-67 | Next.js, TypeScript, React Query, TanStack Table, Firebase Auth |
| @python-reviewer | 68-74 | Pytest unit e integration tests |

---

## Code Patterns

### Pattern 1: Interface BankConnector

```python
# app/connectors/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator

@dataclass
class RawProperty:
    external_code: str
    source_url: str
    raw_data: dict
    bank_code: str
    source_name: str

class BankConnector(ABC):
    bank_code: str

    @abstractmethod
    def discover_sources(self) -> list[str]:
        """Retorna lista de URLs/arquivos a coletar (ex: lista por UF)."""

    @abstractmethod
    def fetch_raw(self, source_url: str) -> bytes:
        """Baixa arquivo bruto (HTML, XLSX, PDF) e retorna bytes."""

    @abstractmethod
    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        """Converte bytes brutos em RawProperty iteráveis."""

    @abstractmethod
    def normalize(self, raw: RawProperty) -> dict:
        """Converte RawProperty para o schema padrão de Property."""
```

### Pattern 2: Content Hash + Deduplicação

```python
# app/agents/deduplicator.py
import hashlib, json

def compute_content_hash(normalized: dict) -> str:
    """Hash SHA-256 dos campos que mudam — exclui timestamps."""
    fields = {
        k: v for k, v in normalized.items()
        if k not in ("first_seen_at", "last_seen_at", "content_hash")
    }
    return hashlib.sha256(
        json.dumps(fields, sort_keys=True, default=str).encode()
    ).hexdigest()

def is_duplicate(session, content_hash: str) -> bool:
    from app.models.property import Property
    return session.query(
        session.query(Property).filter_by(content_hash=content_hash).exists()
    ).scalar()
```

### Pattern 3: Detecção de Mudança

```python
# app/agents/change_detector.py
from app.models.property import Property, PropertyChange

MONITORED_FIELDS = [
    "current_value", "minimum_value", "discount_percent",
    "occupancy_status", "sale_modality", "status", "auction_date"
]

def detect_and_record_changes(session, existing: Property, normalized: dict) -> list[PropertyChange]:
    changes = []
    for field in MONITORED_FIELDS:
        old = getattr(existing, field)
        new = normalized.get(field)
        if str(old) != str(new):
            change = PropertyChange(
                property_id=existing.id,
                field_name=field,
                old_value=str(old),
                new_value=str(new),
            )
            session.add(change)
            changes.append(change)
    return changes
```

### Pattern 4: Camada de Notificação Abstrata

```python
# app/services/notification.py
from abc import ABC, abstractmethod

class NotificationChannel(ABC):
    @abstractmethod
    async def send(self, chat_id: str, message: str) -> bool:
        ...

class TelegramChannel(NotificationChannel):
    def __init__(self, token: str):
        self.token = token

    async def send(self, chat_id: str, message: str) -> bool:
        import httpx
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        r = await httpx.AsyncClient().post(url, json={
            "chat_id": chat_id, "text": message, "parse_mode": "HTML"
        })
        return r.status_code == 200

# Futuramente: EmailChannel, WhatsAppChannel — mesma interface
```

### Pattern 5: Verificação Firebase JWT no FastAPI

```python
# app/api/middleware/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
import firebase_admin
from firebase_admin import auth as firebase_auth

security = HTTPBearer()

async def get_current_user(token = Depends(security)):
    try:
        decoded = firebase_auth.verify_id_token(token.credentials)
        return decoded  # dict com uid, email, etc.
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
```

### Pattern 6: Score Básico de Oportunidade

```python
# app/agents/score_agent.py
def calculate_score(property_data: dict) -> int:
    """
    Score 0-100:
    - Desconto: até 60 pts (1pt por %)
    - Ocupação desocupado: +40 pts
    - Ocupação ocupado: +0 pts
    Score mínimo: 0, máximo: 100
    """
    discount = min(property_data.get("discount_percent") or 0, 60)
    occupancy_bonus = 40 if property_data.get("occupancy_status") == "Desocupado" else 0
    return int(min(discount + occupancy_bonus, 100))
```

### Pattern 7: Endpoint de imóveis com filtros

```python
# app/api/routes/properties.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.models.property import Property
from app.core.database import get_db

router = APIRouter(prefix="/properties", tags=["properties"])

@router.get("/")
def list_properties(
    state: str | None = Query(None),
    city: str | None = Query(None),
    max_price: float | None = Query(None),
    min_discount: float | None = Query(None),
    occupancy_status: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    q = db.query(Property).filter(Property.status == "active")
    if state: q = q.filter(Property.state == state.upper())
    if city: q = q.filter(Property.city.ilike(f"%{city}%"))
    if max_price: q = q.filter(Property.current_value <= max_price)
    if min_discount: q = q.filter(Property.discount_percent >= min_discount)
    if occupancy_status: q = q.filter(Property.occupancy_status == occupancy_status)
    total = q.count()
    items = q.order_by(Property.opportunity_score.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": items, "offset": offset, "limit": limit}
```

---

## Data Flow

```text
FLUXO DE COLETA
───────────────
1. Cloud Scheduler (08h/14h/20h)
   │  Publica mensagem em collect-trigger com payload {bank: "caixa", uf: "SP"}
   ▼
2. Cloud Run Job collect_caixa.py
   │  Lê mensagem Pub/Sub → instancia CaixaConnector
   │  collector.discover_sources() → lista de URLs por UF
   │  collector.fetch_raw(url) → bytes do arquivo XLSX/HTML
   │  Salva bytes em Cloud Storage: raw/caixa/SP/2026-05-26/arquivo.xlsx
   ▼
3. Parser + Normalizador
   │  parser.parse(bytes) → Iterator[RawProperty]
   │  normalizer.normalize(raw) → dict com schema Property
   │  score_agent.calculate_score(dict) → int
   ▼
4. Deduplicador
   │  compute_content_hash(dict) → hash SHA-256
   │  is_duplicate(session, hash)?
   │  ├── SIM → skip (nenhuma ação)
   │  └── NÃO → continua
   ▼
5. Detector de Mudanças
   │  Busca property por external_code no DB
   │  ├── NÃO EXISTE → INSERT em properties (novo imóvel)
   │  └── EXISTE → detect_and_record_changes() → INSERT em property_changes
   ▼
6. Pub/Sub property-events
   │  Publica evento: {property_id, event_type: "new"|"changed", changes: [...]}
   ▼
7. Cloud Run Job alert_agent.py
   │  Consume mensagem de property-events
   │  Busca watchlists que correspondem ao imóvel (cidade/UF/preço/desconto)
   │  Para cada match: gera mensagem → notification.send(chat_id, message)
   │  INSERT em alerts (log do envio)
   ▼
8. Telegram Bot API
   │  Mensagem entregue ao usuário

FLUXO DA API (Dashboard)
─────────────────────────
1. Next.js → axios GET /properties?state=GO&max_price=300000
2. FastAPI → middleware verifica Firebase JWT
3. FastAPI → query Cloud SQL com filtros
4. JSON response → React Query cache → TanStack Table render
```

---

## Integration Points

| Sistema Externo | Tipo de Integração | Autenticação |
|-----------------|-------------------|--------------|
| Caixa Econômica Federal | HTTP scraping (requests + BeautifulSoup) | Nenhuma (página pública) |
| Firebase Auth | SDK `firebase-admin` (verify JWT) | Service Account JSON via Secret Manager |
| Telegram Bot API | HTTPS REST (`api.telegram.org`) | Bot Token via Secret Manager |
| ViaCEP / Nominatim | HTTPS REST (geocodificação) | Nenhuma (gratuito) |
| GCP Cloud SQL | SQLAlchemy + Cloud SQL Python Connector | Service Account IAM |
| GCP Cloud Storage | `google-cloud-storage` SDK | Service Account IAM |
| GCP Pub/Sub | `google-cloud-pubsub` SDK | Service Account IAM |
| GCP Secret Manager | `google-cloud-secret-manager` SDK | Service Account IAM |

---

## Testing Strategy

| Tipo | Escopo | Arquivos | Ferramentas | Meta de Cobertura |
|------|--------|----------|-------------|-------------------|
| Unit | Parser, deduplicador, change detector, score | `tests/unit/` | pytest + fixtures XLSX fake | 90% das funções core |
| Integration | API endpoints, alert agent | `tests/integration/` | pytest + httpx + DB de teste | Todos os acceptance tests AT-001 a AT-010 |
| Manual E2E | Coleta real Caixa → alerta Telegram | — | Execução manual em dev | Happy path + 1 UF pequena |

**Fixtures de teste:**
- Arquivo XLSX fake da Caixa com 3 imóveis (criado em `conftest.py`)
- Imóvel pré-existente no DB para testar detecção de mudança
- Mock do Telegram Bot API (`responses` ou `httpretty`)
- DB PostgreSQL de teste (Docker Compose para CI)

---

## Error Handling

| Erro | Estratégia | Retry? |
|------|-----------|--------|
| Caixa retorna 403 / timeout | Log error, salva em GCS error bucket, continua outras UFs | Não imediato — próxima execução agendada |
| Parsing falha (arquivo malformado) | Log com link do arquivo em GCS, salva raw para diagnóstico | Não |
| Cloud SQL connection failure | Retry exponencial (1s, 2s, 4s) via SQLAlchemy pool | Sim, 3x |
| Telegram send failure | Retry 3x com backoff, registra `alert.status = failed` | Sim, 3x |
| Firebase JWT inválido | HTTP 401 imediato | Não |
| Job Pub/Sub message nack | Pub/Sub faz retry automático até 5x, depois envia à DLQ | Sim (Pub/Sub gerencia) |
| Score cálculo com dados nulos | `min()` e `or 0` defensivos — nunca levanta exceção | N/A |

---

## Configuration

| Config Key | Tipo | Default | Descrição |
|------------|------|---------|-----------|
| `DATABASE_URL` | string | — | Cloud SQL connection string (via Secret Manager) |
| `GCS_BUCKET_RAW` | string | `radar-raw` | Bucket para arquivos brutos da Caixa |
| `PUBSUB_PROJECT_ID` | string | — | GCP Project ID |
| `PUBSUB_TOPIC_COLLECT` | string | `collect-trigger` | Topic de disparo de coleta |
| `PUBSUB_TOPIC_EVENTS` | string | `property-events` | Topic de eventos de imóveis |
| `TELEGRAM_BOT_TOKEN` | string | — | Token do bot (via Secret Manager) |
| `FIREBASE_CREDENTIALS` | string | — | JSON da service account Firebase (via Secret Manager) |
| `CAIXA_REQUEST_DELAY_MS` | int | `1000` | Delay entre requisições (ms) — respeita rate limit |
| `CAIXA_MAX_RETRIES` | int | `3` | Tentativas por URL antes de falhar |
| `ALERT_MAX_RETRIES` | int | `3` | Tentativas de envio Telegram |
| `SCORE_DISCOUNT_MAX_POINTS` | int | `60` | Peso máximo para desconto no score |
| `SCORE_OCCUPANCY_BONUS` | int | `40` | Bonus para imóvel desocupado |
| `TELEGRAM_TOKEN_TTL_SECONDS` | int | `900` | TTL do token de vinculação (15 min) |
| `API_CORS_ORIGINS` | string | `https://radarimovel.com.br` | Origins permitidas (separadas por vírgula) |

---

## Security Considerations

- **Secrets Management:** Nenhum secret em variável de ambiente direta — todos via Secret Manager, lidos no startup do container
- **IAM mínimo:** cada serviço tem service account própria com apenas as permissões necessárias (princípio do menor privilégio)
- **Cloud SQL private IP:** banco não exposto à internet — acesso apenas via VPC Connector
- **Firebase JWT:** verificado em cada requisição da API — `firebase-admin.verify_id_token()` valida assinatura, expiração e projeto
- **CORS:** configurado para o domínio do frontend apenas — sem wildcard em produção
- **Rate limiting na Caixa:** `CAIXA_REQUEST_DELAY_MS` de 1s entre requisições — respeito aos servidores públicos
- **PII (LGPD):** coluna `users.email` é PII — nunca logar, nunca retornar em endpoints públicos, deletar ao desativar conta
- **GCS public access:** bucket `radar-raw` é privado — arquivos acessíveis apenas via service account do job

---

## Observability

| Aspecto | Implementação |
|---------|--------------|
| Logging | JSON estruturado com `structlog` → Cloud Logging. Campos obrigatórios: `service`, `job`, `bank`, `uf`, `level`, `message` |
| Métricas de coleta | Log de linha por execução: `imóveis_coletados`, `novos`, `alterados`, `erros`, `duração_ms` |
| Alertas de falha | Cloud Monitoring alert policy: job com exit code != 0 → notificação por e-mail ao admin |
| Rastreamento de alertas | Tabela `alerts` com `sent_at`, `channel`, `status` (success/failed) — auditável via API admin |
| Health check | `GET /health` na API retorna DB status + última coleta bem-sucedida |

---

## Pipeline Architecture

### DAG de Coleta

```text
Cloud Scheduler (3x/dia)
        │
        ▼
  Pub/Sub collect-trigger
   (1 msg por UF: SP, RJ, MG...)
        │
        ▼ (paralelo, 1 job por UF)
  Cloud Run Jobs collect_caixa
    ├── fetch_raw → Cloud Storage
    ├── parse → RawProperty[]
    ├── normalize → Property dict
    ├── deduplicate (content_hash)
    ├── detect_changes → PropertyChange[]
    ├── score → opportunity_score
    ├── upsert → Cloud SQL
    └── publish → property-events

  property-events
        │
        ▼
  Cloud Run Job alert_agent
    ├── match watchlists
    ├── format message
    ├── send Telegram
    └── log → alerts table
```

### Estratégia Incremental

| Tabela | Estratégia | Chave | Lookback |
|--------|-----------|-------|----------|
| `properties` | Upsert por `external_code + bank_id` | `content_hash` | N/A — detecta mudança por hash |
| `property_changes` | Insert-only | `property_id + detected_at` | N/A |
| `alerts` | Insert-only | `user_id + property_id + sent_at` | N/A |

### Schema Evolution Plan

| Tipo de Mudança | Estratégia | Rollback |
|----------------|-----------|----------|
| Nova coluna | `ADD COLUMN` com `DEFAULT NULL` via Alembic, backfill assíncrono | `DROP COLUMN` |
| Nova tabela | Migration Alembic padrão | `DROP TABLE` |
| Mudança de tipo | Dual-write + migração gradual | Reverter migration |
| Remoção de coluna | Deprecar no código primeiro, remover após 1 sprint | Re-add com migration |

### Data Quality Gates

| Gate | Threshold | Ação em Falha |
|------|-----------|--------------|
| Imóveis coletados por UF > 0 | > 0 registros | Log error + alerta admin (possível mudança de formato Caixa) |
| Duplicate rate < 5% | < 5% de hashes duplicados por execução | Log warning (possível bug no parser) |
| Alerta delivery rate > 95% | > 95% de alertas com status success | Log + retry automático |
| Parsing failures < 1% | < 1% de registros com erro | Log + salvar raw para diagnóstico |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-05-26 | design-agent | Initial version — 74 arquivos, 4 agentes, arquitetura GCP serverless completa |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_MVP_FASE1_CAIXA.md`
