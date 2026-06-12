# DESIGN: V2 — Melhor do Mercado + Céu Azul + Painel Admin

> Especificação técnica para levar o Radar Imóvel à paridade com os líderes (calculadora,
> mapa, multicanal, carteira), somar diferenciais céu azul (curva preditiva, RAG no edital),
> expandir fontes (leiloeiros, judiciais, novas bases) e criar o painel admin de níveis de
> acesso (planos comerciais com feature flags + RBAC interno).

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | V2_MELHOR_DO_MERCADO |
| **Date** | 2026-06-11 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_V2_MELHOR_DO_MERCADO.md](./DEFINE_V2_MELHOR_DO_MERCADO.md) |
| **Status** | ✅ Shipped (2026-06-11, Onda 1) |

**Execução em 4 ondas** (cada onda é um `/build` independente e shippável):

| Onda | Workstream | Entrega |
|------|------------|---------|
| **1** | WS1 — Admin & Níveis de Acesso | Planos, entitlements, RBAC, auditoria, painel admin |
| **2** | WS2 — Paridade competitiva | Calculadora, mapa de busca, WhatsApp/push, export, matrícula IA, Kanban |
| **3** | WS4 — Máximo de fontes | SourceConnector, 5 leiloeiros, ofertas multi-fonte, dedup v2 |
| **4** | WS3 — Céu azul | Curva preditiva, "Pergunte ao edital", Radar Index, SLA de alerta |

> A Onda 1 vem primeiro porque o gating por plano é pré-requisito para monetizar tudo
> que as Ondas 2–4 entregam. A Onda 3 vem antes dos itens céu azul que dependem de
> volume de dados (curva preditiva melhora com mais fontes).

---

## Architecture Overview

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                       RADAR IMÓVEL V2 — VISÃO GERAL                        │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  COLETA (Onda 3)                 NÚCLEO EXISTENTE          ENTREGA         │
│  ┌──────────────┐                                                          │
│  │ 7 bancos      │──┐   ┌─────────────┐   ┌────────────┐  ┌─────────────┐ │
│  │ 5+ leiloeiros │──┼──►│ SourceConn. │──►│ dedup v2   │─►│ properties  │ │
│  │ TJ SP/RJ/MG   │──┘   │ REGISTRY    │   │ (+offers)  │  │ + offers    │ │
│  └──────────────┘       └─────────────┘   └────────────┘  └──────┬──────┘ │
│                                                                   │        │
│  INTELIGÊNCIA (Onda 4)                                            ▼        │
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────┐    ┌─────────────┐  │
│  │ curva preditiva │  │ RAG edital/  │  │ score m²  │    │ Pub/Sub     │  │
│  │ (job batch)     │  │ matrícula    │  │ hiperlocal│    │ events      │  │
│  └─────────────────┘  └──────────────┘  └───────────┘    └──────┬──────┘  │
│                                                                  ▼         │
│  API FastAPI ──── ENTITLEMENTS GATE (Onda 1) ────────────  ┌────────────┐ │
│  toda rota passa por require_feature / consume_quota       │ alertas    │ │
│  ┌──────────────────────────────────────────────┐          │ telegram   │ │
│  │ users ── subscriptions ── plans (flags+limits)│          │ whatsapp   │ │
│  │ users.role (admin/operador/suporte/user)      │          │ e-mail/push│ │
│  │ audit_log │ usage_counters                    │          └────────────┘ │
│  └──────────────────────────────────────────────┘                          │
│                       ▲                                                     │
│  FRONTEND Next.js ────┘                                                     │
│  /admin (painel: planos, usuários, papéis, auditoria, métricas)            │
│  FeatureGate + usePlan() → esconde/CTA upgrade (Onda 2: calc, mapa, kanban)│
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology | Onda |
|-----------|---------|------------|------|
| `app/entitlements/` | Planos, assinaturas, flags, quotas, RBAC, auditoria | SQLAlchemy + FastAPI deps | 1 |
| `app/api/routes/admin_plans.py` + `admin_users.py` | CRUD de planos, atribuição de assinatura, papéis | FastAPI | 1 |
| `frontend/app/admin/*` | Painel admin (planos, usuários, auditoria, métricas) | Next.js + TanStack | 1 |
| `app/calculator/` | Viabilidade: custos por UF, ROI/TIR/payback, aluguel | Python puro + tabela editável | 2 |
| `app/services/whatsapp.py` + `push.py` | Novos canais de notificação | Meta Cloud API + FCM | 2 |
| `app/connectors/caixa/matricula_extractor.py` | IA de matrícula (reusa pipeline do edital) | Gemini structured output | 2 |
| `frontend/app/busca-mapa/` + `carteira/` | Mapa interativo de busca + Kanban | Leaflet + dnd | 2 |
| `app/connectors/base.py` (evoluído) | `SourceConnector` genérico (bank/auctioneer/court) | ABC existente | 3 |
| `app/connectors/{zuk,mega,sodre,fidalgo,frazao}/` | Conectores leiloeiros | BeautifulSoup/Playwright | 3 |
| `app/agents/deduplicator.py` v2 + `property_offers` | 1 imóvel, N ofertas multi-fonte | PostGIS + fuzzy match | 3 |
| `app/prediction/` + `jobs/predict_drops.py` | Curva de desconto preditiva | Heurística → sklearn | 4 |
| `app/rag/` + rota `/properties/{id}/ask` | "Pergunte ao edital" com citações | Vertex AI Vector Search + Gemini | 4 |
| `jobs/build_radar_index.py` | Índice mensal público de deságio | SQL agregado + página pública | 4 |

---

## Key Decisions

### Decision 1: Autorização 100% no Postgres; Firebase só autentica

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-11 |

**Context:** Precisamos de papel (RBAC) e plano (entitlements) por usuário. Firebase Auth já
verifica identidade (`get_current_user`).

**Choice:** `users.role` (enum) e `subscriptions → plans` no Postgres. O middleware carrega
papel + entitlements na mesma query da autenticação. Firebase continua só emitindo JWT.

**Rationale:** Mudanças de plano/papel têm efeito imediato (sem esperar refresh de token);
auditável; testável sem mock de Firebase.

**Alternatives Rejected:**
1. Firebase custom claims — propagação só no refresh do token (até 1h de defasagem), limite de 1000 bytes, e admin teria que chamar Admin SDK para cada mudança.
2. Serviço de feature flag SaaS (LaunchDarkly etc.) — custo e dependência externa para algo que é regra de negócio nossa (plano), não experimento.

**Consequences:**
- +1 query por request (mitigada por `joinedload` na query de usuário já existente)
- Downgrade/upgrade instantâneo — requisito do AT-004

### Decision 2: Feature flags e limites como JSONB no plano (config em banco, sem deploy)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-11 |

**Context:** AT-001 exige criar plano novo com flags refletindo sem deploy.

**Choice:** Tabela `plans` com `features JSONB` (`{"risk_score": true, "export": false, ...}`)
e `limits JSONB` (`{"alerts_per_day": 50, "watchlists": 10, "dd_reports_per_month": 5}`).
Catálogo de chaves válidas em `app/entitlements/catalog.py` (única fonte de verdade, validada
no CRUD do admin).

**Rationale:** Flag nova = 1 entrada no catálogo + uso no código; plano novo = só INSERT.
JSONB evita migração por flag.

**Alternatives Rejected:**
1. Colunas booleanas fixas em `plans` — migração Alembic a cada feature nova.
2. Tabela N×N `plan_features` — mais "correto" relacionalmente, mas a leitura é sempre o conjunto inteiro; JSONB lê em 1 acesso e o catálogo dá a validação que a FK daria.

**Consequences:**
- Validação de chaves vive em código (catálogo) — typo em flag falha no CRUD, não silenciosamente
- Sem histórico de mudanças no JSONB em si → coberto pelo `audit_log` (Decision 4)

### Decision 3: Quotas de uso no Postgres (`usage_counters`), não no Redis

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-11 |

**Context:** Limites como "50 alertas/dia" e "5 relatórios/mês" precisam de contadores por
usuário/feature/período.

**Choice:** Tabela `usage_counters (user_id, feature, period_key, count)` com UPSERT atômico
(`INSERT ... ON CONFLICT ... SET count = count + 1 RETURNING count`). `period_key` =
`"2026-06-11"` (diário) ou `"2026-06"` (mensal).

**Rationale:** Volume baixo (milhares de incrementos/dia), consistência transacional com a
operação que consome a quota, zero infra nova. Redis/Memorystore já existe mas é usado só
para token Telegram — promovê-lo a dependência crítica de billing é prematuro.

**Alternatives Rejected:**
1. Redis INCR — mais rápido, porém contagem divergente do banco em caso de falha parcial e mais um ponto de falha para acerto de cobrança futura.

**Consequences:**
- Se virar gargalo (>100 req/s), migrar para Redis com flush assíncrono — interface `QuotaStore` isola isso

### Decision 4: Auditoria por tabela `audit_log` alimentada na camada de serviço (não trigger)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-11 |

**Context:** AT-005 — toda ação administrativa registrada com quem/o quê/antes/depois.

**Choice:** `audit_log (id, actor_user_id, action, entity_type, entity_id, before JSONB, after JSONB, created_at)` + helper `audit(db, actor, action, entity, before, after)` chamado
explicitamente em cada endpoint admin.

**Rationale:** Explícito e legível; captura o ator autenticado (trigger de banco não conhece
o usuário da request); JSONB before/after atende o teste de aceitação diretamente.

**Alternatives Rejected:**
1. Triggers PostgreSQL — não capturam `actor` sem `SET LOCAL`, frágil com pool de conexões.
2. Event sourcing completo — complexidade desproporcional.

**Consequences:**
- Disciplina de chamada manual — coberta por teste de integração que varre rotas admin mutantes e exige registro

### Decision 5: `SourceConnector` por generalização do contrato atual (rename + namespace), não rewrite

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-11 |

**Context:** O pipeline discover→fetch→parse→normalize do `BankConnector` serve igualmente
para leiloeiros e tribunais. 7 conectores e o job genérico já dependem dele.

**Choice:** `BankConnector` ganha atributos `source_type: str` (`"bank"|"auctioneer"|"court"`)
e `source_code: str`; alias `SourceConnector = BankConnector` durante a transição. Registry
passa a chavear por `source_code` simples (códigos não colidem: `caixa`, `zuk`, `tjsp`).
Tabela `banks` é generalizada por migração para `sources` (rename + coluna `source_type`),
com VIEW `banks` de compatibilidade até a Onda 3 terminar.

**Rationale:** Zero retrabalho nos 7 conectores prontos; o job `collect_bank.py` vira
`collect_source.py` com shim retrocompatível (mesmo padrão usado na Fase 3 com
`collect_caixa.py`).

**Alternatives Rejected:**
1. Hierarquia nova `SourceConnector` ← `BankConnector`/`AuctioneerConnector` — herança sem diferença real de contrato; os 4 métodos são idênticos.
2. Tabela `auctioneers` separada de `banks` — duplicaria FKs em `properties`/`sources` e quebraria queries existentes.

**Consequences:**
- Migração 008 com rename de tabela exige janela de deploy coordenada API+jobs (aceitável: produto pré-lançamento)

### Decision 6: Multi-fonte = `property_offers` (1 imóvel, N ofertas) com dedup em 2 estágios

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-11 |

**Context:** AT-007/AT-011 — o mesmo imóvel publicado pela Caixa e por um leiloeiro deve ser
1 registro com 2 ofertas e 1 alerta.

**Choice:** Nova tabela `property_offers (property_id, source_id, price, modality,
auction_date, url, active, ...)`. O preço "principal" do imóvel = menor oferta ativa
(coluna derivada `properties.best_price`, atualizada pelo deduplicator). Dedup em 2 estágios:
(1) determinístico — match por `matricula+cartorio` ou `external_code` da mesma origem;
(2) probabilístico — bucket por geohash do endereço geocodificado + `pg_trgm similarity`
do endereço normalizado ≥ 0.85 + mesma área ±5%.

**Rationale:** Estágio 1 resolve a maioria (Caixa publica matrícula); estágio 2 cobre
leiloeiros que omitem matrícula. Threshold configurável; falso-merge é pior que duplicata,
então empates ficam separados e marcados `possible_duplicate_of` para revisão no admin.

**Alternatives Rejected:**
1. Dedup só por endereço string — endereços de leiloeiro são sujos ("Av." vs "Avenida", complemento).
2. ML de entity resolution — sem dataset rotulado ainda; heurística + fila de revisão gera o dataset.

**Consequences:**
- `properties.current_price` é substituído por `best_price` derivado — migração tem backfill
- Painel admin ganha fila "possíveis duplicatas" (Onda 3)

### Decision 7: Curva preditiva começa por modelo de sobrevivência heurístico, não ML

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-11 |

**Context:** A-002 do DEFINE: volume de `property_changes` ainda em formação; mas o processo
da Caixa tem etapas determinísticas (1º leilão → 2º leilão → venda online → licitação aberta,
com descontos típicos por transição).

**Choice:** `app/prediction/price_drop.py` calcula P(queda em 30/60/90d) combinando:
(a) tabela de transição de modalidade por banco (priors documentados), ajustada por
(b) estatística empírica Kaplan-Meier sobre `property_changes` agrupada por banco+modalidade+UF,
com peso crescente conforme o N empírico cresce. Output versionado em `price_predictions`
(property_id, horizon, probability, expected_drop_pct, model_version, basis JSONB explicando).

**Rationale:** Entrega valor no dia 1 com explicabilidade ("baseado em 312 imóveis similares,
68% caíram de preço na transição para venda online"), e o próprio uso acumula o dataset para
um modelo sklearn na v2 (mesma tabela de output, `model_version` distingue).

**Alternatives Rejected:**
1. Gradient boosting já — overfit garantido com N pequeno e zero explicabilidade para o usuário.
2. Só regras estáticas — desperdiça o histórico real que já coletamos.

**Consequences:**
- Backtest (critério ≥70% acerto direcional) roda no próprio job com split temporal e grava métricas em log estruturado

### Decision 8: RAG com citação obrigatória — recusa responder sem trecho-fonte

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-11 |

**Context:** AT-009 — resposta deve citar cláusula do edital; ≥90% das respostas com citação.

**Choice:** Chunks do edital/matrícula (já extraídos nas Fases 2 e Onda 2) são embedados
(`text-embedding-005`) e indexados no Vertex AI Vector Search com namespace por
`property_id`. Endpoint `POST /properties/{id}/ask`: retrieve top-k (k=6) → Gemini com
`response_schema` `{answer, citations[{chunk_id, quote}], not_found: bool}`. Se
`citations` vazio e `not_found=false`, a API descarta e responde "não consta no edital".

**Rationale:** O schema força o modelo a se comprometer com a fonte; validação server-side
de que cada `quote` existe textualmente no chunk elimina citação alucinada.

**Alternatives Rejected:**
1. Chat livre sobre o PDF inteiro no contexto — editais grandes estouram custo/latência e não dá garantia de citação verificável.
2. pgvector no Cloud SQL — viável, mas Vector Search já está na stack planejada e separa carga de busca do OLTP. (Revisitar se o custo do Vector Search incomodar: pgvector é o fallback documentado.)

**Consequences:**
- Custo por pergunta controlado por quota de plano (`ask_per_day`) — entitlements da Onda 1
- Indexação acontece no `process_editais` (extensão), não em job novo

### Decision 9: WhatsApp via Meta Cloud API com template pré-aprovado; push via FCM Web Push

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-11 |

**Context:** Alertas multicanal (AT-010). WhatsApp exige conta Business verificada e
templates aprovados; conversas iniciadas pela empresa são cobradas.

**Choice:** `WhatsAppChannel(NotificationChannel)` chamando Graph API com template
`novo_imovel_alerta` (variáveis: cidade, preço, desconto, link). Push web via Firebase Cloud
Messaging (SDK Firebase já está no frontend). Preferência de canais por usuário em
`users.notification_channels JSONB` com fallback Telegram→e-mail se canal falhar.

**Rationale:** Reusa a abstração `NotificationChannel` existente (1 classe nova por canal);
FCM é grátis e o SDK já está no bundle.

**Alternatives Rejected:**
1. Twilio/Z-API para WhatsApp — intermediário cobra por cima; Z-API (não oficial) arrisca ban.
2. E-mail próprio via SMTP — SendGrid já planejado na stack; entra como `EmailChannel` na mesma onda.

**Consequences:**
- A-004 do DEFINE: registro Meta Business inicia já na Onda 1 (lead time); se atrasar, Onda 2 shipa com Telegram/e-mail/push e WhatsApp liga depois por flag

### Decision 10: Tabelas de custo da calculadora editáveis no admin (seed YAML → banco)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-11 |

**Context:** Custos de ITBI/cartório variam por UF e mudam anualmente (A-003). Smart Leilões
trata isso como dado estático de produto.

**Choice:** `cost_tables (uf, year, itbi_pct, registry_table JSONB, notes, updated_by)`
seedada de `app/calculator/seeds/costs_2026.yaml` na migração; painel admin edita (com
auditoria). Calculadora lê do banco com cache em memória de 15 min.

**Rationale:** Corrigir alíquota de um estado vira operação de admin, não deploy; auditoria
de quem mudou custo é requisito implícito de confiança no número.

**Alternatives Rejected:**
1. YAML hardcoded — qualquer correção exige release.

**Consequences:**
- Lançamos com os 10 estados de maior volume preenchidos e validados; demais com default conservador marcado `estimated=true` na resposta da API (transparência no frontend)

---

## File Manifest

### Onda 1 — Admin & Níveis de Acesso (28 arquivos)

| # | File | Action | Purpose | Agent | Deps |
|---|------|--------|---------|-------|------|
| 1 | `app/entitlements/__init__.py` | Create | Exporta API do módulo | @python-developer | — |
| 2 | `app/entitlements/catalog.py` | Create | Catálogo de feature flags e quotas válidas (fonte de verdade) | @python-developer | — |
| 3 | `app/models/plan.py` | Create | `Plan`, `Subscription`, `UsageCounter`, `AuditLog` | @python-developer | 2 |
| 4 | `app/models/user.py` | Modify | `role` enum + `notification_channels` + rel. subscription | @python-developer | 3 |
| 5 | `migrations/versions/008_plans_rbac.py` | Create | Tabelas novas + `users.role` + seed planos Free/Pro/Premium | @database-reviewer | 3,4 |
| 6 | `app/entitlements/service.py` | Create | `get_entitlements(user)`, `has_feature`, `consume_quota` (UPSERT) | @python-developer | 3 |
| 7 | `app/entitlements/audit.py` | Create | Helper `audit(db, actor, action, entity, before, after)` | @python-developer | 3 |
| 8 | `app/api/middleware/auth.py` | Modify | Carrega role+plan no `get_current_user`; deps `require_role`, `require_feature`, `consume_quota` | @python-developer | 6 |
| 9 | `app/api/routes/admin_plans.py` | Create | CRUD planos (valida contra catálogo, audita) | @python-developer | 6,7,8 |
| 10 | `app/api/routes/admin_users.py` | Create | Listar usuários, atribuir plano/expiração, mudar papel | @python-developer | 6,7,8 |
| 11 | `app/api/routes/admin_audit.py` | Create | Consulta paginada do audit_log | @python-developer | 7,8 |
| 12 | `app/api/routes/admin_metrics.py` | Create | Métricas: usuários/plano, alertas, saúde dos conectores | @python-developer | 8 |
| 13 | `app/api/routes/admin.py` | Modify | Proteger rotas existentes com `require_role("operador")` | @python-developer | 8 |
| 14 | `app/api/main.py` | Modify | Registrar novos routers | @python-developer | 9–12 |
| 15 | `app/api/routes/users.py` | Modify | `/users/me` retorna plano, flags e limites (para o frontend gatear) | @python-developer | 6 |
| 16 | `jobs/expire_subscriptions.py` | Create | Job diário: rebaixa assinaturas expiradas p/ Free (AT-004) | @python-developer | 3 |
| 17 | `frontend/lib/entitlements.ts` | Create | Tipos + fetch de `/users/me`; mapa de flags | @typescript-reviewer | 15 |
| 18 | `frontend/hooks/usePlan.ts` | Create | Hook `usePlan()` com TanStack Query | @typescript-reviewer | 17 |
| 19 | `frontend/components/FeatureGate.tsx` | Create | Wrapper: renderiza children ou CTA de upgrade | @typescript-reviewer | 18 |
| 20 | `frontend/app/admin/planos/page.tsx` | Create | CRUD visual de planos (flags/limites do catálogo) | @typescript-reviewer | 17 |
| 21 | `frontend/app/admin/usuarios/page.tsx` | Create | Busca usuário, atribui plano/papel/expiração | @typescript-reviewer | 17 |
| 22 | `frontend/app/admin/auditoria/page.tsx` | Create | Tabela paginada do audit log | @typescript-reviewer | 17 |
| 23 | `frontend/app/admin/page.tsx` | Modify | Vira dashboard de métricas + navegação do painel | @typescript-reviewer | 17 |
| 24 | `infra/terraform/scheduler.tf` | Modify | Scheduler do `expire_subscriptions` | @gcp-data-architect | 16 |
| 25 | `tests/unit/test_entitlements.py` | Create | Catálogo, has_feature, consume_quota (corrida/limite) | @test-generator | 6 |
| 26 | `tests/integration/test_admin_plans.py` | Create | AT-001/002/003/005: CRUD, gating 403, RBAC, auditoria | @test-generator | 9–13 |
| 27 | `tests/integration/test_subscription_lifecycle.py` | Create | AT-004: atribuição manual e expiração | @test-generator | 10,16 |
| 28 | `tests/unit/test_audit.py` | Create | before/after JSONB, ator obrigatório | @test-generator | 7 |

### Onda 2 — Paridade competitiva (24 arquivos)

| # | File | Action | Purpose | Agent | Deps |
|---|------|--------|---------|-------|------|
| 29 | `app/calculator/__init__.py` + `engine.py` | Create | ROI, TIR, payback, simulação venda/aluguel | @python-developer | — |
| 30 | `app/calculator/seeds/costs_2026.yaml` | Create | ITBI/cartório por UF (10 estados validados) | @python-developer | — |
| 31 | `app/models/cost_table.py` | Create | `CostTable` editável | @python-developer | 30 |
| 32 | `migrations/versions/009_cost_tables.py` | Create | Tabela + seed do YAML | @database-reviewer | 31 |
| 33 | `app/api/routes/calculator.py` | Create | `POST /properties/{id}/viability` (gated `calculator`) | @python-developer | 29,31 |
| 34 | `app/api/routes/admin_costs.py` | Create | Admin edita tabela de custos (auditado) | @python-developer | 31 |
| 35 | `app/services/whatsapp.py` | Create | `WhatsAppChannel` (Meta Cloud API, template) | @python-developer | — |
| 36 | `app/services/email.py` | Create | `EmailChannel` (SendGrid) | @python-developer | — |
| 37 | `app/services/push.py` | Create | `PushChannel` (FCM) | @python-developer | — |
| 38 | `app/services/notification.py` | Modify | Registry de canais + preferência/fallback por usuário | @python-developer | 35–37 |
| 39 | `app/agents/alert_agent.py` | Modify | Multicanal conforme `notification_channels` + quota | @python-developer | 38 |
| 40 | `app/connectors/caixa/matricula_extractor.py` | Create | Gemini structured output p/ matrícula (reusa edital) | @ai-prompt-specialist-gcp | — |
| 41 | `app/schemas/matricula.py` | Create | Schema Pydantic da matrícula (ônus, proprietários, área) | @python-developer | 40 |
| 42 | `jobs/process_matriculas.py` | Create | Job consumidor (mesmo padrão process_editais) | @python-developer | 40,41 |
| 43 | `app/api/routes/properties.py` | Modify | Export CSV/Excel (gated `export`) + campos matrícula | @python-developer | 41 |
| 44 | `app/models/portfolio.py` | Create | `PortfolioItem` (estágio Kanban, custos reais, notas) | @python-developer | — |
| 45 | `migrations/versions/010_portfolio_matricula.py` | Create | portfolio + colunas matrícula em documents | @database-reviewer | 41,44 |
| 46 | `app/api/routes/portfolio.py` | Create | CRUD carteira (gated `portfolio`) | @python-developer | 44 |
| 47 | `frontend/app/busca-mapa/page.tsx` | Create | Busca por mapa (clusters, raio, filtros) — reusa RiskMap | @typescript-reviewer | — |
| 48 | `frontend/components/ViabilityCalculator.tsx` | Create | Calculadora na página do imóvel | @typescript-reviewer | 33 |
| 49 | `frontend/app/carteira/page.tsx` + `components/KanbanBoard.tsx` | Create | Kanban da carteira | @typescript-reviewer | 46 |
| 50 | `frontend/components/MatriculaSection.tsx` | Create | Dados da matrícula (graceful degradation) | @typescript-reviewer | 43 |
| 51 | `infra/terraform/{pubsub,cloud_run,secret_manager}.tf` | Modify | Tópico matrícula-events, job, secrets WhatsApp/SendGrid | @gcp-data-architect | 42 |
| 52 | `tests/unit/test_calculator.py` + `test_channels.py` + `tests/integration/test_portfolio.py` | Create | AT-006/010 + canais com mock | @test-generator | 29,38,46 |

### Onda 3 — Máximo de fontes (22 arquivos)

| # | File | Action | Purpose | Agent | Deps |
|---|------|--------|---------|-------|------|
| 53 | `app/connectors/base.py` | Modify | `source_type`/`source_code`; alias `SourceConnector` | @python-developer | — |
| 54 | `app/connectors/__init__.py` | Modify | `SOURCE_REGISTRY` (mantém `CONNECTOR_REGISTRY` como alias) | @python-developer | 53 |
| 55 | `migrations/versions/011_sources_offers.py` | Create | banks→sources (+VIEW compat), `property_offers`, `best_price` backfill, `possible_duplicate_of` | @database-reviewer | — |
| 56 | `app/models/{bank.py→source.py, property.py}` | Modify | Modelo `Source`; `PropertyOffer`; `best_price` | @python-developer | 55 |
| 57–61 | `app/connectors/{zuk,mega,sodre,fidalgo,frazao}/` (collector/parser/normalizer cada) | Create | 5 conectores leiloeiros (gate jurídico ToS antes de ativar cada um) | @python-developer | 53,54 |
| 62 | `app/connectors/tjsp/` | Create | Editais de hasta pública TJ-SP (piloto judicial) | @python-developer | 53 |
| 63 | `app/agents/deduplicator.py` | Modify | Dedup 2 estágios (matrícula → geohash+trgm); gera offers | @python-developer | 55,56 |
| 64 | `jobs/collect_source.py` | Create | Job genérico por fonte (`collect_bank.py` vira shim) | @python-developer | 54 |
| 65 | `app/risk/sources/datajud.py` | Create | DataJud/CNJ na dimensão jurídica do risco | @python-developer | — |
| 66 | `app/api/routes/admin_dedup.py` | Create | Fila de possíveis duplicatas (merge/separar, auditado) | @python-developer | 63 |
| 67 | `frontend/app/admin/duplicatas/page.tsx` | Create | Revisão visual de duplicatas | @typescript-reviewer | 66 |
| 68 | `frontend/app/imoveis/[id]/page.tsx` | Modify | Mostrar N ofertas por imóvel (fonte, preço, modalidade) | @typescript-reviewer | 56 |
| 69 | `infra/terraform/scheduler.tf` | Modify | Schedulers por fonte nova (`setproduct` já existente) | @gcp-data-architect | 64 |
| 70 | `tests/unit/test_{zuk,mega,sodre,fidalgo,frazao,tjsp}_parser.py` + `test_dedup_v2.py` + `tests/integration/test_offers.py` | Create | Parsers com fixtures HTML reais + AT-007/011 | @test-generator | 57–63 |

### Onda 4 — Céu azul (16 arquivos)

| # | File | Action | Purpose | Agent | Deps |
|---|------|--------|---------|-------|------|
| 71 | `app/prediction/__init__.py` + `price_drop.py` | Create | Sobrevivência heurística+empírica, output explicável | @python-developer | Onda 3 |
| 72 | `app/prediction/priors.yaml` | Create | Transições de modalidade e descontos típicos por banco | @python-developer | — |
| 73 | `migrations/versions/012_predictions.py` | Create | `price_predictions` (+ índice property/horizon) | @database-reviewer | 71 |
| 74 | `jobs/predict_drops.py` | Create | Job semanal + backtest com split temporal (log de métricas) | @python-developer | 71,73 |
| 75 | `app/rag/__init__.py` + `indexer.py` + `chat.py` | Create | Chunking/embedding/Vector Search + ask com citação validada | @ai-prompt-specialist-gcp | — |
| 76 | `jobs/process_editais.py` | Modify | Indexa chunks no Vector Search após extração | @python-developer | 75 |
| 77 | `app/api/routes/ask.py` | Create | `POST /properties/{id}/ask` (gated `ask` + quota `ask_per_day`) | @python-developer | 75 |
| 78 | `jobs/build_radar_index.py` | Create | Índice mensal de deságio por região/banco → tabela + JSON público | @python-developer | Onda 3 |
| 79 | `app/api/routes/radar_index.py` | Create | Endpoint público (sem auth) do índice | @python-developer | 78 |
| 80 | `app/agents/alert_agent.py` | Modify | Carimbo de latência "detectado há X min" no alerta (SLA visível) | @python-developer | — |
| 81 | `frontend/components/PriceDropForecast.tsx` | Create | Card de probabilidade 30/60/90d com base explicada | @typescript-reviewer | 74 |
| 82 | `frontend/components/AskEdital.tsx` | Create | Chat com citações destacadas no imóvel | @typescript-reviewer | 77 |
| 83 | `frontend/app/radar-index/page.tsx` | Create | Página pública do índice (SEO) | @typescript-reviewer | 79 |
| 84 | `infra/terraform/{vertex.tf,scheduler.tf}` | Create/Modify | Vector Search index/endpoint + schedulers novos | @gcp-data-architect | 75 |
| 85 | `tests/unit/test_price_drop.py` + `test_rag_citations.py` | Create | Backtest sintético + validação citação-existe-no-chunk (AT-008/009) | @test-generator | 71,75 |
| 86 | `tests/integration/test_ask_endpoint.py` | Create | Quota, not_found, citação obrigatória | @test-generator | 77 |

**Total: ~86 arquivos** (28 + 24 + 22 + 16, com itens 57–61 e 70 contando múltiplos)

---

## Agent Assignment Rationale

| Agent | Files | Why This Agent |
|-------|-------|----------------|
| @python-developer | Maioria backend | Padrões do projeto: dataclasses, SQLAlchemy 2.0, FastAPI deps |
| @database-reviewer | Migrações 008–012 | Renames com VIEW de compat, backfill, índices (trgm, geohash) |
| @typescript-reviewer | Frontend admin/gates/kanban/chat | Next.js 14 App Router + TanStack já em uso |
| @ai-prompt-specialist-gcp | matrícula extractor, RAG | Structured output Gemini + citação verificável |
| @gcp-data-architect | Terraform (Vector Search, schedulers, secrets) | Infra modular existente |
| @test-generator | Suítes por onda | pytest asyncio_mode=auto, fixtures HTML reais (padrão das fases) |
| @security-reviewer | Revisão da Onda 1 inteira | RBAC/entitlements/auditoria são superfície de segurança |

---

## Code Patterns

### Pattern 1: Dependencies de autorização (Onda 1 — usa em toda rota nova)

```python
# app/api/middleware/auth.py (extensão)
from app.entitlements.service import get_entitlements, consume as consume_usage

ROLE_ORDER = {"user": 0, "suporte": 1, "operador": 2, "admin": 3}

def require_role(min_role: str):
    async def dep(user: User = Depends(get_current_user)) -> User:
        if ROLE_ORDER.get(user.role, 0) < ROLE_ORDER[min_role]:
            raise HTTPException(403, detail={"code": "FORBIDDEN_ROLE"})
        return user
    return dep

def require_feature(flag: str):
    async def dep(
        user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        ent = get_entitlements(db, user)
        if not ent.features.get(flag, False):
            raise HTTPException(403, detail={"code": "PLAN_LIMIT", "feature": flag})
        return user
    return dep

def consume_quota(feature: str, period: str = "day"):
    async def dep(
        user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        if not consume_usage(db, user, feature, period):  # UPSERT atômico; False = estourou
            raise HTTPException(429, detail={"code": "QUOTA_EXCEEDED", "feature": feature})
        return user
    return dep

# Uso:
# @router.get("/properties/export")
# def export(user: User = Depends(require_feature("export"))): ...
```

### Pattern 2: Catálogo de entitlements (fonte de verdade)

```python
# app/entitlements/catalog.py
from dataclasses import dataclass

@dataclass(frozen=True)
class FeatureDef:
    key: str
    description: str

@dataclass(frozen=True)
class QuotaDef:
    key: str
    period: str  # "day" | "month"
    description: str

FEATURES = {f.key: f for f in [
    FeatureDef("risk_score", "Score de risco multidimensional"),
    FeatureDef("due_diligence_pdf", "Relatório PDF de due diligence"),
    FeatureDef("export", "Export CSV/Excel"),
    FeatureDef("calculator", "Calculadora de viabilidade"),
    FeatureDef("portfolio", "Carteira Kanban"),
    FeatureDef("realtime_alerts", "Alertas em tempo real (<15min)"),
    FeatureDef("whatsapp_channel", "Alertas por WhatsApp"),
    FeatureDef("ask", "Pergunte ao edital (RAG)"),
    FeatureDef("price_forecast", "Curva de desconto preditiva"),
    FeatureDef("api_access", "API B2B"),
]}

QUOTAS = {q.key: q for q in [
    QuotaDef("alerts_per_day", "day", "Alertas enviados por dia"),
    QuotaDef("watchlists", "static", "Watchlists ativas"),
    QuotaDef("dd_reports_per_month", "month", "Relatórios due diligence/mês"),
    QuotaDef("ask_per_day", "day", "Perguntas ao edital/dia"),
]}

def validate_plan_config(features: dict, limits: dict) -> list[str]:
    errors = [f"flag desconhecida: {k}" for k in features if k not in FEATURES]
    errors += [f"quota desconhecida: {k}" for k in limits if k not in QUOTAS]
    return errors
```

### Pattern 3: Consumo de quota atômico (Decision 3)

```python
# app/entitlements/service.py
from sqlalchemy import text

def consume(db: Session, user: User, feature: str, period: str) -> bool:
    limit = get_entitlements(db, user).limits.get(feature)
    if limit is None:
        return True  # sem limite definido no plano = ilimitado
    period_key = _period_key(period)  # "2026-06-11" ou "2026-06"
    row = db.execute(text("""
        INSERT INTO usage_counters (user_id, feature, period_key, count)
        VALUES (:uid, :feat, :pk, 1)
        ON CONFLICT (user_id, feature, period_key)
        DO UPDATE SET count = usage_counters.count + 1
        RETURNING count
    """), {"uid": str(user.id), "feat": feature, "pk": period_key}).one()
    if row.count > limit:
        return False
    db.commit()
    return True
```

### Pattern 4: FeatureGate no frontend

```tsx
// frontend/components/FeatureGate.tsx
"use client";
import { usePlan } from "@/hooks/usePlan";

export function FeatureGate({ feature, children }: { feature: string; children: React.ReactNode }) {
  const { plan, isLoading } = usePlan();
  if (isLoading) return null;
  if (!plan?.features?.[feature]) {
    return (
      <div className="rounded-lg border border-dashed p-6 text-center">
        <p className="text-sm text-gray-600">Disponível no plano superior</p>
        <a href="/configuracoes/plano" className="text-blue-600 font-medium">Fazer upgrade →</a>
      </div>
    );
  }
  return <>{children}</>;
}
```

### Pattern 5: Conector de leiloeiro (Onda 3 — mesmo contrato dos bancos)

```python
# app/connectors/zuk/__init__.py
from app.connectors.base import SourceConnector  # alias de BankConnector

class ZukConnector(SourceConnector):
    source_type = "auctioneer"
    source_code = "zuk"
    bank_code = "zuk"  # compat até remover o alias

    def discover_sources(self) -> list[str]: ...
    def fetch_raw(self, source_url: str) -> bytes: ...
    def parse(self, raw_bytes, source_url): ...      # yield RawProperty
    def normalize(self, raw) -> dict: ...            # usa normalize_utils existentes
```

### Pattern 6: Resposta RAG com citação verificada (Onda 4)

```python
# app/rag/chat.py — validação server-side da citação
def validate_citations(answer: AskResponse, chunks: dict[str, str]) -> AskResponse:
    valid = [c for c in answer.citations
             if c.chunk_id in chunks and _normalize(c.quote) in _normalize(chunks[c.chunk_id])]
    if not valid and not answer.not_found:
        return AskResponse(answer="Não consta no edital deste imóvel.",
                           citations=[], not_found=True)
    return answer.model_copy(update={"citations": valid})
```

---

## Data Flow (fluxo crítico: imóvel novo multi-fonte → alerta gated)

```text
1. Scheduler dispara collect_source --source=zuk
   │
2. ZukConnector: discover → fetch → parse → normalize (schema padrão)
   │
3. Deduplicator v2:
   │   estágio 1: matrícula/external_code → match? anexa PropertyOffer ao imóvel existente
   │   estágio 2: geohash + trgm ≥0.85 → match? anexa offer | empate? marca possible_duplicate_of
   │   sem match → cria Property + Offer; recalcula best_price
   │
4. ChangeDetector publica em property-events (novo imóvel / best_price caiu)
   │
5. process_alerts: casa watchlists → para cada usuário:
   │   require entitlement: realtime_alerts? envia já : agrega no digest diário
   │   consume_quota("alerts_per_day") → estourou? registra suppressed
   │   canais do usuário (telegram/whatsapp/email/push) com fallback
   │
6. Alerta inclui "detectado há X min" (SLA visível) — meta < 15 min ponta a ponta
```

---

## Integration Points

| External System | Integration Type | Authentication | Onda |
|-----------------|-----------------|----------------|------|
| Meta WhatsApp Cloud API | REST (Graph API), template aprovado | Token em Secret Manager | 2 |
| SendGrid | REST | API key em Secret Manager | 2 |
| FCM (push) | Firebase Admin SDK (já presente) | Service account existente | 2 |
| Sites de leiloeiros (5) | Scraping HTTP/Playwright | — (gate jurídico ToS por fonte) | 3 |
| TJ-SP (hasta pública) | Scraping/PDF | — (dado público) | 3 |
| DataJud / CNJ | API pública REST | API key pública | 3 |
| Vertex AI (Gemini + embeddings + Vector Search) | SDK google-cloud-aiplatform | IAM `aiplatform.user` (já concedido) | 2, 4 |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | entitlements, calculator, parsers, dedup, prediction, RAG citations | `tests/unit/*` | pytest | 80% nos módulos novos |
| Integration | matriz plano×feature×rota (AT-001..005), portfolio, offers, ask | `tests/integration/*` | pytest + SQLite/pg + httpx | Todos os ATs do DEFINE |
| Contract | toda rota mutante de admin gera audit_log (varredura automática do router) | `tests/integration/test_admin_audit_contract.py` | pytest | 100% rotas admin |
| Backtest | curva preditiva (split temporal, ≥70% direcional) | dentro de `jobs/predict_drops.py --backtest` | pytest marker `slow` | gate de release da Onda 4 |
| E2E manual | fluxo upgrade de plano → feature liberada; alerta WhatsApp real | checklist no BUILD_REPORT | — | happy path por onda |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Entitlement negado | 403 `{code: PLAN_LIMIT, feature}` — frontend mostra CTA | Não |
| Quota estourada | 429 `{code: QUOTA_EXCEEDED}` — alerta vira digest, não some | Não |
| WhatsApp falha (template/token) | Fallback Telegram → e-mail; log `notification.fallback` | 1× |
| Scraper leiloeiro quebrou (layout mudou) | Job marca fonte `degraded`, alerta admin no painel de métricas; demais fontes seguem | Próximo ciclo |
| Dedup empate | Nunca merge automático — fila `possible_duplicate_of` no admin | — |
| Citação RAG não verifica | Resposta degradada "não consta no edital" (nunca alucinação) | Não |
| Vector Search indisponível | `/ask` responde 503 com mensagem amigável; edital estruturado continua visível | Sim (client) |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `DEFAULT_PLAN_CODE` | string | `free` | Plano de novos usuários e de downgrade |
| `ENTITLEMENTS_CACHE_TTL_S` | int | `60` | Cache em memória dos entitlements por user |
| `DEDUP_TRGM_THRESHOLD` | float | `0.85` | Similaridade mínima do estágio 2 |
| `DEDUP_AREA_TOLERANCE` | float | `0.05` | Tolerância de área no match probabilístico |
| `WHATSAPP_ENABLED` | bool | `false` | Liga canal após aprovação Meta |
| `PREDICTION_MIN_SAMPLES` | int | `30` | N mínimo p/ usar estatística empírica sobre o prior |
| `RAG_TOP_K` | int | `6` | Chunks recuperados por pergunta |
| `ALERT_SLA_TARGET_MIN` | int | `15` | Meta de latência exposta no alerta |

---

## Security Considerations

- **Onda 1 é superfície de segurança**: revisão obrigatória do @security-reviewer antes do merge (RBAC, IDOR em rotas admin — todo `entity_id` validado contra existência, paginação com limite).
- `audit_log` é **append-only** (sem UPDATE/DELETE na API; grant restrito no Postgres).
- E-mail é PII (comentário já existente no model): rotas admin de usuários retornam e-mail mascarado para papel `suporte`, completo só para `admin`.
- Tokens WhatsApp/SendGrid exclusivamente via Secret Manager (padrão existente).
- LGPD nas fontes judiciais: persistir número do processo e dados do imóvel; **nunca** nomes das partes (constraint de schema: sem colunas para partes).
- `/radar-index` é público: servir de tabela agregada materializada — nunca query ao vivo sobre dados granulares.
- Rate limit de `/ask` também por IP (além de quota por plano) contra abuso de custo Gemini.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | structlog JSON (padrão): eventos `entitlement.denied`, `quota.exceeded`, `audit.*`, `dedup.merged/flagged`, `notification.fallback`, `source.degraded` |
| Metrics | Painel admin de métricas (Onda 1) lê agregados do Postgres; Cloud Monitoring para latência de alerta (publish→sent) com alarme se p50 > 15 min |
| Tracing | Latência ponta-a-ponta do alerta carimbada no próprio payload (`detected_at` → `sent_at`) e logada por etapa |

---

## Pipeline Architecture

### DAG por onda 3 (coleta multi-fonte)

```text
[Scheduler por fonte] → collect_source --source=X
   → SourceConnector(X) → normalize → Deduplicator v2 → properties/offers
   → ChangeDetector → Pub/Sub property-events → process_alerts (gated)
                                   ↘ edital-events → process_editais → RAG index (Onda 4)
```

### Incremental Strategy

| Dataset | Strategy | Key | Notes |
|---------|----------|-----|-------|
| property_offers | upsert por (property_id, source_id) | external_code | `active=false` quando some da fonte |
| price_predictions | full refresh semanal por model_version | property_id+horizon | mantém histórico de versões |
| radar_index | append mensal | (period, region, source) | tabela materializada pública |

### Data Quality Gates

| Gate | Tool | Threshold | Action on Failure |
|------|------|-----------|-------------------|
| Parser yield = 0 em fonte ativa | job collect_source | 0 imóveis | marca `degraded` + alerta admin |
| % imóveis sem geocoding por fonte | job semanal | > 20% | alerta admin (dedup estágio 2 degrada) |
| Dedup: taxa de fila de revisão | métrica admin | > 10% das inserções | revisar thresholds |
| Backtest preditivo | predict_drops --backtest | < 70% direcional | bloqueia exposição da feature (flag off) |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-11 | design-agent | Versão inicial — 4 ondas, 10 decisões, ~86 arquivos |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_V2_MELHOR_DO_MERCADO.md` — começar pela **Onda 1** (o build deve tratar cada onda como um ciclo completo com testes e report próprios).
