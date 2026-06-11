# Radar Imóvel

> Plataforma de inteligência para monitorar leilões e vendas de imóveis de bancos públicos brasileiros (Caixa, Banco do Brasil, BRB, BNB, Banco da Amazônia, Banrisul, Banestes). O sistema coleta automaticamente os imóveis disponíveis, detecta mudanças de preço e status, calcula um score de oportunidade, lê editais com IA e envia alertas personalizados por Telegram/WhatsApp/e-mail.
>
> **Status:** Fases 1–3 **shipped** + features de Fase 4 em andamento. Fase 1 (Caixa), Fase 2 (IA nos editais via Gemini) e Fase 3 (conectores para os 7 bancos) concluídas com suíte de testes passando. Da Fase 4 já foram entregues o Mapa de Risco multidimensional (score 0–100) e a ingestão de geodados públicos (`radar-load-geodata`). Pendente: validar coleta real dos bancos em produção e provisionar a infra GCP. Repo: https://github.com/ProjectDataengineerUK/RadarImovel

---

## Stack

Legenda: ✅ em uso · 🔭 planejado para fases futuras.

- **Frontend:** ✅ Next.js 14 + TypeScript + Tailwind CSS + TanStack Table/Query + Firebase SDK + axios + Recharts + Leaflet (mapa de calor)
- **Backend:** ✅ Python 3.12 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 + structlog, no Cloud Run
- **Coleta:** ✅ Python + BeautifulSoup + Pandas + openpyxl + pdfplumber (Playwright como dependência opcional/fallback)
- **Banco de dados:** ✅ Cloud SQL PostgreSQL + PostGIS (migrations Alembic) · 🔭 BigQuery (analytics)
- **Fila/eventos:** ✅ Google Cloud Pub/Sub + Cloud Run Jobs + Cloud Scheduler
- **Orquestração:** 🔭 Google Cloud Workflows
- **IA/LLM:** ✅ Gemini via Vertex AI (leitura de editais com `response_schema` estruturado)
- **Documentos:** 🔭 Google Cloud Document AI (OCR para PDFs escaneados — hoje a extração é texto nativo via pdfplumber)
- **Busca semântica:** 🔭 Vertex AI Vector Search (RAG sobre editais)
- **Arquivos brutos:** ✅ Google Cloud Storage
- **Cache:** ✅ Redis / Memorystore (token de vínculo Telegram)
- **Autenticação:** ✅ Firebase Auth (verificação de JWT via firebase-admin)
- **Alertas:** ✅ Telegram Bot · 🔭 WhatsApp, SendGrid (e-mail) — camada de notificação já abstraída
- **Segurança:** ✅ IAM + Secret Manager · 🔭 Cloud Armor
- **Observabilidade:** ✅ Cloud Logging · 🔭 Cloud Monitoring
- **CI/CD:** ✅ Cloud Build (`cloudbuild.yaml`) + Terraform (`infra/terraform/`)

## Estrutura atual

```
radar-imovel/
├── app/
│   ├── core/             # config, database (SQLAlchemy + Cloud SQL connector), logging
│   ├── models/           # base, bank, property, user, document (SQLAlchemy)
│   ├── connectors/       # base.py (interface BankConnector) + registry + 7 bancos (caixa, bb, brb, bnb, basa, banrisul, banestes)
│   ├── agents/           # deduplicator, change_detector, score_agent, alert_agent
│   ├── services/         # notification (canal abstrato), telegram, geocoding
│   └── api/              # main.py (FastAPI), middleware/auth.py, routes/ (properties, watchlists, users, alerts, admin)
├── jobs/                 # collect_bank.py (genérico), process_alerts, process_editais, enrich_details, calculate_risk, load_geodata
├── migrations/           # Alembic (env.py + versions/001_initial_schema.py)
├── frontend/             # Next.js 14: app/ (login, dashboard, imoveis, alertas, configuracoes, admin), components/, hooks/, lib/
├── infra/terraform/      # cloud_sql, cloud_run, pubsub, cloud_storage, scheduler, iam, secret_manager, variables, outputs, main
├── tests/                # unit/ (parser, agentes) + integration/ (api, alert_agent) + conftest.py
├── Dockerfile.api / Dockerfile.job / cloudbuild.yaml
├── pyproject.toml        # deps Python (extras: api, job, dev, playwright) + ruff + pytest + mypy
└── context.md            # Especificação completa do produto (gerada no ChatGPT)
```

## Arquivos-chave

| Arquivo | Função |
|---------|--------|
| `context.md` | Especificação completa do produto: fontes, agentes, arquitetura GCP, banco de dados, dashboard e fluxos |
| `.claude/sdd/features/` | Documentos SDD das Fases 1–3 (`BRAINSTORM_`, `DEFINE_`, `DESIGN_`); features de Fase 4 já arquivadas em `.claude/sdd/archive/` |
| `app/connectors/base.py` | Interface abstrata `BankConnector` (discover_sources / fetch_raw / parse / normalize) — contrato para novos bancos |
| `migrations/versions/001_initial_schema.py` | Schema completo: properties, property_changes, banks, sources, users, watchlists, alerts, documents |
| `pyproject.toml` | Dependências e configuração de ferramentas (ruff, pytest, mypy) |

## Convenções

- **Linter:** Ruff (`line-length=100`, regras `E,F,I,UP`) — `[tool.ruff]` no `pyproject.toml`
- **Type-check:** mypy (`python_version=3.12`, `strict=false`); frontend: `tsc --noEmit`
- **Testes:** pytest (`asyncio_mode=auto`, `testpaths=tests`) — unit + integration
- **Formatter Python:** não há autoformatter dedicado; seguir o estilo do Ruff

## Como rodar

```bash
# --- Backend (API) ---
pip install -e ".[api,dev]"
alembic upgrade head                          # aplica o schema (requer DATABASE_URL)
uvicorn app.api.main:app --reload             # API em http://localhost:8000

# --- Jobs de coleta/alerta (extra "job") ---
pip install -e ".[job]"
python -m jobs.collect_caixa                  # coleta Caixa por UF
python -m jobs.process_alerts                 # consome property-events e envia alertas

# --- Testes / lint ---
pytest                                        # suíte unit + integration
ruff check .                                  # lint

# --- Frontend ---
cd frontend && npm install && npm run dev     # dashboard em http://localhost:3000
```

---

## Bancos monitorados (em ordem de prioridade)

| Banco | Estratégia de coleta |
|-------|---------------------|
| **Caixa** | Prioridade máxima: lista completa por UF, calendário de leilões, editais, detalhe do imóvel, leiloeiros credenciados |
| **Banco do Brasil** | Portal oficial + parceiros autorizados |
| **BRB** | Página oficial de imóveis + Feirão BRB (Resale) |
| **Banco do Nordeste** | Página "Bens à Venda" + PDF de relação |
| **Banco da Amazônia** | Editais de venda de bens penhorados, leilão/praça pública |
| **Banrisul** | Página de bens à venda (lançada em abr/2026) |
| **Banestes** | Publicações legais e editais de alienação |

## Fases do MVP

- **Fase 1:** ✅ shipped — Caixa: coleta de lista por UF, detecção de novos imóveis, alerta Telegram, painel simples
- **Fase 2:** ✅ shipped (2026-06-08) — leitura de editais com Gemini (`edital_extractor`), score enriquecido, pipeline Pub/Sub `edital-events` → job `radar-process-editais`
- **Fase 3:** ✅ shipped (2026-06-08) — conectores para os 7 bancos via `CONNECTOR_REGISTRY` + job genérico `collect_bank` (94/94 testes)
- **Fase 4:** 🔨 em andamento — já entregues: Mapa de Risco multidimensional 0–100 (2026-06-10) e ingestão de geodados públicos `radar-load-geodata` (2026-06-11); pendentes: preço por m², relatórios, comparação com mercado

Relatórios de ship em `.claude/sdd/reports/` e features arquivadas em `.claude/sdd/archive/`.

---

## Agentes recomendados (agentcode)

| Agente | Quando usar |
|--------|-------------|
| `@the-planner` | Planejar implementação do MVP por fase |
| `@design-agent` | Especificar arquitetura técnica detalhada de cada componente |
| `@brainstorm-agent` | Explorar abordagens antes de decidir (ex: orquestração, scraping estratégico) |
| `@gcp-data-architect` | Provisionar Cloud Run Jobs, Cloud SQL, Pub/Sub, BigQuery, Cloud Storage |
| `@ai-data-engineer-gcp` | Construir pipelines GCP, Cloud Functions, ingestão para BigQuery |
| `@ai-prompt-specialist-gcp` | Otimizar prompts Gemini para leitura de editais e extração de risco |
| `@genai-architect` | Projetar orquestração multiagente (Supervisor → Coletores → LLM → Alertas) |
| `@python-developer` | Implementar coletores, parsers, normalizadores e agentes em Python |
| `@python-reviewer` | Revisar código dos conectores e pipelines |
| `@typescript-reviewer` | Revisar dashboard Next.js |
| `@database-reviewer` | Revisar schema PostgreSQL/PostGIS e queries |
| `@security-reviewer` | Auditar credenciais, IAM, Secret Manager e acesso a fontes públicas |
| `@code-reviewer` | Revisão geral de qualquer código implementado |

## Comandos úteis

| Comando | Quando usar |
|---------|-------------|
| `/brainstorm` | Explorar decisões de arquitetura antes de implementar |
| `/define` | Capturar requisitos de um módulo específico |
| `/design` | Criar especificação técnica detalhada de um agente ou conector |
| `/pipeline` | Projetar pipelines de dados no GCP |
| `/workflow` | Projetar fluxos de agentes LLM com Gemini |
| `/preflight` | Verificar qualidade antes de qualquer PR |
| `/status` | Ver estado atual do projeto |

---

_Gerado por `/start` em 2026-05-26. Atualizado em 2026-06-11 para refletir o ship das Fases 1–3 e o progresso da Fase 4._
