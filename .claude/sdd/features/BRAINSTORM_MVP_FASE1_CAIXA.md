# BRAINSTORM: MVP Fase 1 — Radar Imóvel (Caixa)

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | MVP_FASE1_CAIXA |
| **Date** | 2026-05-26 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input:** Plataforma SaaS para monitorar leilões e vendas de imóveis de bancos públicos brasileiros, com alertas inteligentes, painel web e score de oportunidade. Começar pela Caixa Econômica Federal como fonte prioritária.

**Context Gathered:**
- Projeto em fase de especificação — nenhum código implementado ainda
- Contexto completo do produto documentado em `context.md` (exportação de sessão ChatGPT com arquitetura detalhada)
- GCP escolhido como cloud principal desde o início
- Nome do produto definido: **Radar Imóvel**

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `app/connectors/caixa/`, `app/agents/`, `app/models/`, `frontend/` | Estrutura modular por banco desde o início |
| Relevant KB Domains | GCP, Python, FastAPI, Next.js, PostgreSQL/PostGIS | Stack bem definida |
| IaC Patterns | GCP do zero — sem projeto criado | Terraform ou gcloud CLI para provisionamento inicial |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual o recorte do MVP? | MVP completo Fase 1: Caixa + painel web + alertas Telegram | Escopo full-stack, não só back-end |
| 2 | Para quem é o MVP? | SaaS público — qualquer pessoa pode se cadastrar | Exige autenticação, multi-tenancy, LGPD |
| 3 | A infraestrutura GCP já existe? | GCP do zero — nenhum projeto criado ainda | Provisionamento de infra entra no escopo |
| 4 | Amostras disponíveis? | Nenhuma amostra disponível ainda | Primeiros dados reais virão do conector Caixa |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | N/A | 0 | Serão coletados pela primeira vez pelo conector Caixa |
| Output examples | N/A | 0 | Schema definido no `context.md` como referência |
| Ground truth | N/A | 0 | Não disponível no momento |
| Related code | N/A | 0 | Projeto do zero |

**Como as amostras serão usadas (quando disponíveis):**
- Planilhas/PDFs reais da Caixa para calibrar o parser
- Exemplos de imóveis como fixtures de teste
- Dados normalizados para validar o schema

---

## Approaches Explored

### Approach A: GCP Serverless Full Stack ⭐ Recommended

**Description:** Cloud Run Jobs para coleta, Cloud SQL PostgreSQL+PostGIS para dados, FastAPI no Cloud Run para API, Next.js no Firebase Hosting para frontend, Firebase Auth para autenticação, Pub/Sub + Cloud Scheduler para orquestração.

**Pros:**
- Pay-per-use — custo zero enquanto não há usuários
- Totalmente gerenciado — sem servidor para operar
- Escala automaticamente para SaaS público
- Firebase Auth resolve multi-tenancy e LGPD em horas

**Cons:**
- Setup inicial mais complexo (IAM, projetos, billing, service accounts)
- Vendor lock-in no GCP

**Why Recommended:** O usuário confirmou GCP do zero e SaaS público. É a única abordagem que escala para esse caso de forma profissional e cost-effective.

---

### Approach B: VPS + Docker Compose

**Description:** Servidor único com PostgreSQL, FastAPI, Next.js, Celery+Redis, Nginx.

**Pros:**
- Simples e barato
- Controle total do ambiente

**Cons:**
- Não escala para SaaS público
- Contradiz a escolha de GCP
- Ops manual (backups, SSL, updates)

---

### Approach C: Multi-vendor Gerenciado (Supabase + Vercel + Cloud Run)

**Description:** Cloud Run Jobs para coleta + Supabase (banco + auth + realtime) + Vercel (frontend).

**Pros:**
- Supabase tem auth e realtime prontos
- Vercel simplifica deploy de Next.js

**Cons:**
- Multi-vendor complica billing e segurança
- Supabase tem limitações com PostGIS em produção
- Aumenta dependências externas

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A — GCP Serverless Full Stack |
| **User Confirmation** | 2026-05-26 |
| **Reasoning** | SaaS público + GCP do zero — única abordagem que escala de forma profissional e cost-effective |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Cloud Run Jobs (não Cloud Functions) para coletores | Jobs suportam execuções longas sem timeout de 9min | Cloud Functions — timeout inadequado para scraping |
| 2 | Firebase Auth para autenticação | Resolve multi-tenancy e LGPD com zero código extra | Auth0 — custo mais alto; custom auth — risco de segurança |
| 3 | PostgreSQL + PostGIS desde o início | Suporte a geolocalização sem migração futura | PostgreSQL puro — exigiria migração quando mapa entrar |
| 4 | Interface abstrata `BankConnector` no MVP | Cada banco novo é implementar a interface, sem reescrever pipeline | Código específico por banco — refatoração garantida ao escalar |
| 5 | Schema completo desde o MVP | Migrations em produção são arriscadas | Schema mínimo — alto risco de retrabalho ao crescer |
| 6 | Cloud Storage para arquivos brutos | Pipeline pronto para Document AI entrar sem mudar coleta | Salvar só dados estruturados — perde evidências e trava IA futura |
| 7 | Pub/Sub como mensageria central | Desacopla coletores do pipeline, retry automático, dead-letter queue | Chamadas diretas entre serviços — frágil e sem retry |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Mapa (Leaflet/Mapbox) | Tabela resolve no MVP; PostGIS já está no schema para quando entrar | Yes — Fase 2 |
| Leitura de edital com IA (Gemini + Document AI) | Alta complexidade; GCS já salva arquivos brutos como fundação | Yes — Fase 2 |
| Score avançado de oportunidade | Campo e lógica básica entram no MVP; pesos avançados depois | Yes — Fase 2 |
| Favoritos Kanban | Tabela `favorites` entra no schema; UI Kanban depois | Yes — Fase 2 |
| WhatsApp / E-mail | Telegram resolve no MVP; camada de notificação já abstrai o canal | Yes — Fase 2 |
| Outros bancos (BB, BRB, BNB...) | `BankConnector` abstrato pronto; implementações depois | Yes — Fase 3 |
| BigQuery + analytics | Sem volume histórico para justificar; Cloud SQL exporta para BQ depois | Yes — Fase 3 |
| Comparação com mercado | Alta complexidade jurídica e técnica | Yes — Fase 4 |

---

## Data Engineering Context

### Source Systems

| Source | Type | Volume Estimate | Current Freshness |
|--------|------|-----------------|-------------------|
| Caixa — Lista por UF | XLSX/HTML/PDF (página pública) | ~10k-50k imóveis / coleta | Atualizado periodicamente (sem SLA definido) |
| Caixa — Detalhe do imóvel | HTML (página pública) | 1 request por imóvel | Sob demanda |
| Caixa — Calendário de leilões | PDF/HTML | ~50-200 registros / mês | Publicação eventual |

### Data Flow Sketch

```text
[Caixa UF Lists] → [Cloud Run Job Coletor]
                          ↓
                   [Cloud Storage - raw]
                          ↓
                   [Parser Caixa]
                          ↓
                   [Normalizador]
                          ↓
                   [Deduplicador (content_hash)]
                          ↓
                   [Detector de Mudanças]
                          ↓
               [Cloud SQL PostgreSQL + PostGIS]
                    ↓              ↓
            [Score Básico]   [property_changes]
                    ↓
            [Agente de Alertas]
                    ↓
           [Telegram Bot → Usuário]
```

### Key Data Questions Explored

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Volume esperado? | ~10k-50k imóveis Caixa ativos | Cloud SQL adequado; BigQuery desnecessário no MVP |
| 2 | Frequência de coleta? | Várias vezes ao dia (a definir no /define) | Cloud Scheduler com jobs por UF em paralelo |
| 3 | Quem consome o output? | Usuários SaaS via dashboard + alertas Telegram | API FastAPI + Telegram Bot |

---

## Fundações Arquiteturais (entram no MVP para evitar retrabalho)

| Fundação | Justificativa |
|----------|--------------|
| Interface abstrata `BankConnector` (collect, parse, normalize, save) | Cada banco novo implementa a interface — zero reescrita de pipeline |
| Camada de notificação com abstração de canal | Telegram implementado; WhatsApp/e-mail entram sem reescrita |
| Schema completo: banks, sources, properties, property_changes, documents, alerts, watchlists, users, favorites | Migrations em produção são arriscadas — schema certo desde o início |
| `content_hash` + deduplicação ativa | Histórico corrompido é irrecuperável |
| `property_changes` tracking ativo desde o dia 1 | Dado histórico perdido não volta |
| Cloud Storage para arquivos brutos | Habilita Document AI futuro sem mudar o pipeline de coleta |
| Score básico no schema (campo + cálculo simples de desconto) | Extensível com novos pesos sem migration |
| Estrutura de pastas: connectors/, agents/, models/, services/ | Refatorar estrutura em produção é custoso |
| Pub/Sub + Cloud Run Jobs | Escala, retry automático, DLQ — Cloud Functions não aguenta coletas longas |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| YAGNI — cortes do MVP | ✅ | Aprovado | No |
| Risco de retrabalho futuro | ✅ | Pediu incluir fundações arquiteturais no MVP | Yes — adicionadas todas as fundações |
| MVP revisado com fundações | ✅ | Aprovado | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)

Investidores em imóveis perdem oportunidades de leilões e vendas de bancos públicos porque as informações estão dispersas em múltiplos portais, sem alertas em tempo real e sem análise de risco consolidada.

### Target Users (Draft)

| User | Pain Point |
|------|------------|
| Investidor pessoa física | Não consegue monitorar todos os bancos manualmente |
| Comprador de primeiro imóvel | Não sabe quando aparecem imóveis com desconto na sua cidade |
| Assessor de investimentos | Precisa de visão consolidada para múltiplos clientes |

### Success Criteria (Draft)

- [ ] Sistema coleta imóveis da Caixa automaticamente ao menos 3x ao dia
- [ ] Novo imóvel detectado → alerta Telegram enviado em menos de 30 minutos
- [ ] Mudança de preço detectada e registrada em `property_changes`
- [ ] Usuário consegue filtrar por cidade, UF, valor e desconto mínimo
- [ ] Nenhum imóvel duplicado no banco (content_hash funcional)
- [ ] Interface `BankConnector` documentada e testada para facilitar novos conectores

### Constraints Identified

- GCP do zero — provisionamento de infra entra no escopo do MVP
- Caixa não tem API pública oficial — scraping de HTML/XLSX/PDF necessário
- Termos de uso da Caixa devem ser respeitados (sem scraping agressivo)
- LGPD: dados de usuários (e-mail, watchlists) devem ser tratados corretamente
- Custo GCP deve ser mínimo enquanto não há receita (pay-per-use obrigatório)

### Out of Scope (Confirmed)

- Mapa interativo de imóveis
- Leitura e análise de editais com IA (Gemini/Document AI)
- Score avançado de oportunidade com múltiplos pesos
- Integração com outros bancos (BB, BRB, BNB, Banrisul, Banestes)
- Alertas por WhatsApp ou e-mail
- Comparação com preço de mercado (Zap, OLX, Viva Real)
- BigQuery e relatórios analíticos
- Favoritos Kanban

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 4 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 8 |
| Fundações Arquiteturais Adicionadas | 9 |
| Validations Completed | 3 |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_MVP_FASE1_CAIXA.md`
