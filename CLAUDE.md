# Mastavista (ex-Radar Imóvel)

> Plataforma de inteligência para monitorar leilões e vendas de imóveis de bancos públicos brasileiros (Caixa, Banco do Brasil, BRB, BNB, Banco da Amazônia, Banrisul, Banestes). O sistema coleta automaticamente os imóveis disponíveis, detecta mudanças de preço e status, calcula um score de oportunidade, lê editais com IA e envia alertas personalizados por Telegram/WhatsApp/e-mail.
>
> **Marca:** Mastavista · **Domínio:** mastavista.com.br (IP LB: 34.8.91.61, SSL provisionando)
> **Status:** Fases 1–5 **shipped**. 16 fontes monitoradas (7 bancos + 5 leiloeiros + judicial + TJSP + Lance Certo + Superleilões), detector de 2ª Praça, comparação FipeZap, calculadora ROI, Radar Index por município. 339/339 testes passando. Repo: https://github.com/ProjectDataengineerUK/RadarImovel

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
- **Pagamentos:** 🔭 Stripe (billing por assinatura — planos Free / Pro / Pro Anual)
- **Segurança:** ✅ IAM + Secret Manager · 🔭 Cloud Armor
- **Observabilidade:** ✅ Cloud Logging + Sentinela (DataOps + LLMOps + MLOps dashboards) · 🔭 Cloud Monitoring
- **CI/CD:** ✅ Cloud Build (`cloudbuild.yaml`) + GitHub Actions (`.github/workflows/deploy.yml`) + Terraform (`infra/terraform/`)
- **Infraestrutura de domínio:** ✅ GCP Global HTTPS LB + Serverless NEG → Cloud Run frontend (`infra/terraform/lb_frontend.tf`)

## Estrutura atual

```
radar-imovel/
├── app/
│   ├── core/             # config, database (SQLAlchemy + Cloud SQL connector), logging
│   ├── models/           # base, bank, property, user, document (SQLAlchemy)
│   ├── connectors/       # base.py (interface BankConnector) + registry + 16 fontes (7 bancos + 5 leiloeiros + judicial + tjsp + lance_certo + superleiloes)
│   ├── agents/           # deduplicator, change_detector, score_agent, alert_agent, second_auction_detector
│   ├── services/         # notification (canal abstrato), telegram, geocoding, fipezap
│   └── api/              # main.py (FastAPI), middleware/auth.py, routes/ (properties, watchlists, users, alerts, admin, market, risk)
├── jobs/                 # collect_bank.py (genérico), collect_judicial.py, collect_market_prices.py, process_alerts, process_editais, enrich_details, calculate_risk, load_geodata
├── migrations/           # Alembic (env.py + versions/001_initial_schema.py)
├── frontend/             # Next.js 14: app/ (login, cadastro, dashboard, imoveis, alertas, configuracoes, admin, planos, privacidade, termos), components/ (LandingPage), hooks/, lib/
├── infra/terraform/      # cloud_sql, cloud_run, pubsub, cloud_storage, scheduler, iam, secret_manager, lb_frontend, variables, outputs, main
├── tests/                # unit/ (parser, agentes) + integration/ (api, alert_agent) + conftest.py
├── Dockerfile.api / Dockerfile.job / cloudbuild.yaml
├── pyproject.toml        # deps Python (extras: api, job, dev, playwright) + ruff + pytest + mypy
└── context.md            # Especificação completa do produto (gerada no ChatGPT)
```

## Arquivos-chave

| Arquivo | Função |
|---------|--------|
| `context.md` | Especificação completa do produto: fontes, agentes, arquitetura GCP, banco de dados, dashboard e fluxos |
| `.claude/sdd/features/` | Vazio — pronto para próxima fase. Fases 1–5 arquivadas em `.claude/sdd/archive/` |
| `infra/terraform/lb_frontend.tf` | Load Balancer GCP para mastavista.com.br → Cloud Run frontend (IP: 34.8.91.61) |
| `frontend/components/LandingPage.tsx` | Landing page client component com hero, FAQ, mock de propriedade, nav mobile |
| `frontend/app/cadastro/page.tsx` | Página de signup (Google OAuth + email/senha) |
| `frontend/app/privacidade/page.tsx` | Política de Privacidade (LGPD) |
| `frontend/app/termos/page.tsx` | Termos de Uso |
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
- **Fase 4:** ✅ shipped (2026-06-11) — Mapa de Risco multidimensional 0–100, ingestão de geodados públicos (`radar-load-geodata`)
- **Fase 5:** ✅ shipped (2026-06-15) — 16 fontes (judicial DataJud, Lance Certo, Superleilões, TJSP), detector de 2ª Praça (queda ≥40%), comparação FipeZap, calculadora ROI, Radar Index por município; 339/339 testes
- **Go-to-Market:** ✅ shipped (2026-06-16) — Rebranding para Mastavista, landing page completa, páginas de cadastro/privacidade/termos, Load Balancer GCP + domínio mastavista.com.br, Sentinela observabilidade (DataOps + LLMOps + MLOps)

Relatórios de ship em `.claude/sdd/reports/` e features arquivadas em `.claude/sdd/archive/`.

## Próximos passos sugeridos

1. **DNS**: Adicionar registro A `@ → 34.8.91.61` e `www → 34.8.91.61` no registrar do domínio mastavista.com.br
2. **Stripe**: Integrar billing (webhook + portal do cliente) para os planos Free / Pro / Pro Anual
3. **WhatsApp / e-mail**: Ativar canais de alerta adicionais (já abstraídos em `notification`)
4. **BigQuery**: Analytics sobre imóveis e comportamento de usuários

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

_Gerado por `/start` em 2026-05-26. Atualizado em 2026-06-16 para refletir rebranding Mastavista, go-to-market (Fases 1–5 + GTM shipped), domínio e LB GCP._
