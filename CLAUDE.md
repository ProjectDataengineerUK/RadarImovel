# Radar Imóvel

> Plataforma de inteligência para monitorar leilões e vendas de imóveis de bancos públicos brasileiros (Caixa, Banco do Brasil, BRB, BNB, Banco da Amazônia, Banrisul, Banestes). O sistema coleta automaticamente os imóveis disponíveis, detecta mudanças de preço e status, calcula um score de oportunidade, lê editais com IA e envia alertas personalizados por Telegram/WhatsApp/e-mail. O projeto está na fase de especificação/design — nenhum código foi escrito ainda.

---

## Stack

- **Frontend:** Next.js, TypeScript, Tailwind CSS, shadcn/ui, TanStack Table, React Query, Recharts, Leaflet/Mapbox
- **Backend:** Python + FastAPI, Cloud Run
- **Coleta:** Python + Playwright + BeautifulSoup + Pandas + pdfplumber/PyMuPDF + openpyxl
- **Banco de dados:** Cloud SQL PostgreSQL + PostGIS (dados principais), BigQuery (analytics)
- **Fila/eventos:** Google Cloud Pub/Sub + Cloud Run Jobs + Cloud Scheduler
- **Orquestração:** Google Cloud Workflows
- **IA/LLM:** Gemini via Vertex AI / Gemini Enterprise Agent Platform
- **Documentos:** Google Cloud Document AI (OCR/extração de PDFs)
- **Busca semântica:** Vertex AI Vector Search (RAG sobre editais)
- **Arquivos brutos:** Google Cloud Storage
- **Cache:** Redis / Memorystore
- **Autenticação:** Firebase Auth ou Auth0
- **Alertas:** Telegram Bot, WhatsApp, SendGrid (e-mail)
- **Segurança:** IAM, Secret Manager, Cloud Armor
- **Observabilidade:** Cloud Logging, Cloud Monitoring

## Estrutura proposta

```
radar-imovel/
├── app/
│   ├── agents/           # Supervisor, normalizer, deduplicator, risk, score, alert
│   ├── connectors/       # Um subdiretório por banco (caixa/, banco_brasil/, brb/ ...)
│   ├── models/           # property, bank, document, alert
│   └── services/         # geocoding, notification, market_price
├── frontend/             # Next.js dashboard
├── infra/                # Terraform / GCP configs
└── context.md            # Especificação completa do produto (gerada no ChatGPT)
```

## Arquivos-chave

| Arquivo | Função |
|---------|--------|
| `context.md` | Especificação completa do produto: fontes, agentes, arquitetura GCP, banco de dados, dashboard e fluxos |

## Convenções

- **Linter:** não configurado (projeto em fase de spec)
- **Formatter:** não configurado
- **Testes:** não configurado

## Como rodar

```bash
# Projeto em fase de especificação — nenhum código implementado ainda.
# Próximo passo: implementar MVP fase 1 (Caixa)
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

- **Fase 1:** Caixa — coleta de lista por UF, detecção de novos imóveis, alerta Telegram, painel simples
- **Fase 2:** Caixa com IA — leitura de editais (Document AI + Gemini), score de oportunidade, histórico de mudanças
- **Fase 3:** Todos os bancos — um conector por banco, mesmo pipeline de normalização e alertas
- **Fase 4:** Inteligência de mercado — preço por m², mapa, relatórios, comparação com mercado

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

_Gerado por `/start` em 2026-05-26._
