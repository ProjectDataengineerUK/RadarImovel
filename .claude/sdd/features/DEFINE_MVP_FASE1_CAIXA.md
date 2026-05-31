# DEFINE: MVP Fase 1 — Radar Imóvel (Caixa)

> SaaS público que monitora imóveis da Caixa automaticamente, detecta novidades e mudanças de preço, e envia alertas personalizados via Telegram, com painel web para filtrar e acompanhar oportunidades.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | MVP_FASE1_CAIXA |
| **Date** | 2026-05-26 |
| **Author** | define-agent |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |
| **Source** | BRAINSTORM_MVP_FASE1_CAIXA.md |

---

## Problem Statement

Investidores em imóveis perdem oportunidades de leilões e vendas diretas da Caixa Econômica Federal porque as informações estão em portais dispersos, sem alertas em tempo real e sem histórico de mudanças de preço. O monitoramento manual é inviável dado o volume de imóveis e a frequência de atualizações.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Investidor pessoa física | Compra imóveis abaixo do mercado | Não consegue monitorar a Caixa diariamente — perde lances e vendas diretas |
| Comprador de primeiro imóvel | Busca imóvel com desconto na sua cidade | Não sabe quando aparecem oportunidades na faixa de preço dele |
| Assessor de investimentos | Pesquisa oportunidades para clientes | Precisa de visão consolidada sem acessar múltiplos portais manualmente |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Coletar automaticamente todos os imóveis da Caixa (lista por UF) ao menos 3x ao dia |
| **MUST** | Detectar novos imóveis e mudanças de preço/status e registrar no histórico |
| **MUST** | Enviar alerta Telegram ao usuário quando um imóvel corresponde à watchlist dele |
| **MUST** | Painel web com tabela filtrável (cidade, UF, preço, desconto, ocupação, modalidade) |
| **MUST** | Autenticação SaaS com Firebase Auth — cadastro, login e sessão persistente |
| **MUST** | Watchlist básica: usuário define filtros (cidade/UF, preço máx, desconto mín) |
| **MUST** | Interface abstrata `BankConnector` e schema completo desde o MVP (previne retrabalho) |
| **SHOULD** | Score básico de oportunidade (desconto + ocupação) visível no painel |
| **SHOULD** | Página de detalhe do imóvel com histórico de mudanças |
| **SHOULD** | Admin de coletores: status de cada job, última coleta, erros |
| **COULD** | Notificação quando imóvel favorito muda de preço |

---

## Success Criteria

- [ ] Coletor Caixa executa com sucesso ao menos 3x ao dia, cobrindo todas as UFs disponíveis
- [ ] Novo imóvel detectado → alerta Telegram entregue em menos de 30 minutos
- [ ] Mudança de preço ou status → registrada em `property_changes` com valor anterior e novo
- [ ] Nenhum imóvel duplicado no banco (content_hash único e verificado antes de inserir)
- [ ] Usuário consegue filtrar imóveis por cidade, UF, valor máximo e desconto mínimo no painel
- [ ] Usuário se cadastra, faz login, cria watchlist e conecta Telegram em menos de 5 minutos
- [ ] Interface `BankConnector` documentada — novo conector pode ser criado implementando 4 métodos (collect, parse, normalize, save)
- [ ] Falha no coletor não derruba o sistema — job falha de forma isolada com log de erro
- [ ] Cloud Storage armazena todos os arquivos brutos coletados (HTML/XLSX/PDF) com link acessível

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Coleta automática por UF | Cloud Scheduler dispara às 08h | Cloud Run Job executa coleta de lista Caixa para cada UF | Imóveis salvos em `properties` com content_hash, arquivos brutos em Cloud Storage |
| AT-002 | Detecção de novo imóvel | Imóvel X não existe em `properties` | Coletor encontra imóvel X na lista da Caixa | Imóvel inserido em `properties`, alerta disparado via Pub/Sub para o Agente de Alertas |
| AT-003 | Alerta Telegram por watchlist | Usuário tem watchlist: Goiânia/GO, ≤ R$300k, ≥ 30% desconto | Imóvel novo em Goiânia/GO, R$190k, 42% desconto é detectado | Mensagem Telegram enviada ao usuário em < 30 min |
| AT-004 | Detecção de mudança de preço | Imóvel X salvo com `current_value = 200000` | Coletor encontra mesmo imóvel com `current_value = 180000` | Registro criado em `property_changes` (campo, valor antigo, valor novo, timestamp); alerta enviado se imóvel está em watchlist |
| AT-005 | Deduplicação por content_hash | Imóvel X existe com `content_hash = "abc123"` | Coletor encontra mesmo imóvel sem alteração | Nenhum registro duplicado criado; nenhum alerta disparado |
| AT-006 | Falha isolada do coletor | Caixa retorna erro 403 para UF-SP | Cloud Run Job de coleta SP executa | Job falha com log de erro no Cloud Logging; outros jobs de outras UFs não são afetados; mensagem enviada à DLQ do Pub/Sub |
| AT-007 | Cadastro e onboarding | Usuário acessa o dashboard pela primeira vez | Usuário se cadastra com e-mail via Firebase Auth | Conta criada; usuário redirecionado para criar primeira watchlist |
| AT-008 | Conexão do Telegram | Usuário está logado e acessa configurações | Usuário clica em "Conectar Telegram" | Sistema gera token único; usuário envia token para o bot Radar Imóvel; bot confirma vinculação |
| AT-009 | Visualização de detalhe | Usuário clica em imóvel na tabela | Página de detalhe carrega | Exibe dados do imóvel, histórico de mudanças de `property_changes`, link oficial e score |
| AT-010 | Admin de coletores | Admin acessa painel de operação | Carrega status dos jobs | Exibe: banco, última coleta, status (OK/Erro), imóveis coletados, link para logs |

---

## Out of Scope

- Mapa interativo de imóveis (Leaflet/Mapbox) — Fase 2
- Leitura e análise de editais com IA (Gemini + Document AI) — Fase 2
- Score avançado de oportunidade com múltiplos fatores (liquidez de cidade, comparação com mercado) — Fase 2
- Favoritos com Kanban de pipeline de decisão — Fase 2
- Alertas por WhatsApp ou e-mail — Fase 2
- Conectores para outros bancos (BB, BRB, BNB, Banrisul, Banestes) — Fase 3
- BigQuery e relatórios analíticos históricos — Fase 3
- Comparação com preço de mercado (Zap, OLX, Viva Real) — Fase 4
- Pagamento / monetização — não entra no MVP

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Técnico | GCP do zero — nenhum projeto criado | Provisionamento de infra (IAM, billing, Cloud SQL, Cloud Run, Firebase) entra no escopo do MVP |
| Técnico | Caixa não tem API pública oficial | Coleta via scraping de HTML/XLSX/PDF — parser deve ser resiliente a mudanças de layout |
| Legal | Termos de uso da Caixa devem ser respeitados | Sem scraping agressivo: rate limiting, user-agent legítimo, intervalo entre requisições |
| Legal | LGPD — dados de usuários (e-mail, watchlists) | Política de privacidade obrigatória; dados de usuários não devem ser expostos |
| Custo | GCP pay-per-use obrigatório enquanto não há receita | Cloud Run Jobs (por execução), Cloud SQL shared-core, Firebase Auth free tier |
| Técnico | Coletas podem demorar > 9 min por UF | Cloud Run Jobs (sem timeout de 9 min) — não Cloud Functions |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `app/connectors/caixa/`, `app/agents/`, `app/models/`, `app/services/`, `frontend/` | Estrutura modular por banco; connectors/ esconde implementação específica atrás da interface BankConnector |
| **KB Domains** | GCP (Cloud Run, Cloud SQL, Pub/Sub, Cloud Storage), Python (FastAPI, Playwright, BeautifulSoup), Next.js, PostgreSQL/PostGIS | Padrões GCP serverless event-driven + stack Python/Next.js |
| **IaC Impact** | Novos recursos GCP — Cloud Run Jobs, Cloud SQL, Cloud Storage, Pub/Sub, Cloud Scheduler, Firebase, Secret Manager | Terraform ou gcloud CLI para provisionamento inicial do projeto GCP do zero |

---

## Data Contract

### Source Inventory

| Source | Type | Volume Estimado | Freshness | Owner |
|--------|------|----------------|-----------|-------|
| Caixa — Lista de imóveis por UF | XLSX / HTML / PDF (página pública) | ~10k–50k imóveis / coleta | Caixa atualiza periodicamente (sem SLA) | Caixa Econômica Federal |
| Caixa — Detalhe do imóvel | HTML (página pública) | 1 request por imóvel novo | Sob demanda | Caixa Econômica Federal |

### Schema Contract — Tabelas Principais

**`properties`** (tabela central)

| Column | Type | Constraints | PII? |
|--------|------|-------------|------|
| id | UUID | NOT NULL, PK | No |
| bank_id | UUID | NOT NULL, FK → banks | No |
| source_id | UUID | NOT NULL, FK → sources | No |
| external_code | VARCHAR(100) | NOT NULL | No |
| title | VARCHAR(255) | nullable | No |
| property_type | VARCHAR(50) | NOT NULL | No |
| address | TEXT | nullable | No |
| neighborhood | VARCHAR(100) | nullable | No |
| city | VARCHAR(100) | NOT NULL | No |
| state | CHAR(2) | NOT NULL | No |
| latitude | DECIMAL(10,7) | nullable | No |
| longitude | DECIMAL(10,7) | nullable | No |
| area_total | DECIMAL(10,2) | nullable | No |
| area_private | DECIMAL(10,2) | nullable | No |
| bedrooms | SMALLINT | nullable | No |
| parking_spaces | SMALLINT | nullable | No |
| appraisal_value | DECIMAL(15,2) | nullable | No |
| minimum_value | DECIMAL(15,2) | NOT NULL | No |
| current_value | DECIMAL(15,2) | NOT NULL | No |
| discount_percent | DECIMAL(5,2) | nullable | No |
| occupancy_status | VARCHAR(30) | NOT NULL | No |
| sale_modality | VARCHAR(50) | NOT NULL | No |
| edital_number | VARCHAR(50) | nullable | No |
| auction_date | DATE | nullable | No |
| auctioneer_name | VARCHAR(100) | nullable | No |
| auctioneer_url | TEXT | nullable | No |
| official_url | TEXT | NOT NULL | No |
| edital_url | TEXT | nullable | No |
| risk_level | VARCHAR(20) | nullable | No |
| opportunity_score | SMALLINT | nullable | No |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | No |
| first_seen_at | TIMESTAMPTZ | NOT NULL | No |
| last_seen_at | TIMESTAMPTZ | NOT NULL | No |
| content_hash | VARCHAR(64) | NOT NULL, UNIQUE | No |

**`property_changes`** (histórico de mudanças)

| Column | Type | Constraints | PII? |
|--------|------|-------------|------|
| id | UUID | NOT NULL, PK | No |
| property_id | UUID | NOT NULL, FK → properties | No |
| field_name | VARCHAR(50) | NOT NULL | No |
| old_value | TEXT | nullable | No |
| new_value | TEXT | nullable | No |
| detected_at | TIMESTAMPTZ | NOT NULL | No |

**`users`** (autenticação via Firebase — apenas referência)

| Column | Type | Constraints | PII? |
|--------|------|-------------|------|
| id | UUID | NOT NULL, PK | No |
| firebase_uid | VARCHAR(128) | NOT NULL, UNIQUE | No |
| email | VARCHAR(255) | NOT NULL | **Yes** |
| telegram_chat_id | BIGINT | nullable | No |
| created_at | TIMESTAMPTZ | NOT NULL | No |

**`watchlists`**

| Column | Type | Constraints | PII? |
|--------|------|-------------|------|
| id | UUID | NOT NULL, PK | No |
| user_id | UUID | NOT NULL, FK → users | No |
| state | CHAR(2) | nullable | No |
| city | VARCHAR(100) | nullable | No |
| max_price | DECIMAL(15,2) | nullable | No |
| min_discount | DECIMAL(5,2) | nullable | No |
| property_type | VARCHAR(50) | nullable | No |
| bank_id | UUID | nullable, FK → banks | No |
| active | BOOLEAN | NOT NULL, DEFAULT true | No |

### Freshness SLAs

| Layer | Target | Measurement |
|-------|--------|-------------|
| Raw (Cloud Storage) | Arquivo bruto salvo em < 5 min após início do job | Timestamp do upload vs. início do job |
| Staging (properties) | Imóvel normalizado inserido em < 10 min após coleta | `first_seen_at` vs. início do job |
| Alerta | Telegram enviado em < 30 min após detecção | `alerts.sent_at` vs. `property_changes.detected_at` |

### Completeness Metrics

- 100% das UFs disponíveis na Caixa coletadas por execução de coleta
- Zero imóveis com `content_hash` duplicado em `properties`
- 100% das mudanças de campo detectadas registradas em `property_changes`

---

## Assumptions

| ID | Assumption | Se errada, impacto | Validado? |
|----|------------|-------------------|-----------|
| A-001 | A Caixa mantém a estrutura atual de listas por UF (XLSX ou HTML com campos estáveis) | Parser quebra — necessário fallback e alertas de parsing failure | [ ] |
| A-002 | Cloud SQL shared-core (db-f1-micro) suporta o volume do MVP (< 50k imóveis, < 100 usuários) | Upgrade para db-g1-small necessário | [ ] |
| A-003 | Telegram Bot API está disponível e gratuita para o volume do MVP | Nenhum — é gratuita até limites muito altos | [x] |
| A-004 | Firebase Auth Free Tier (10k usuários/mês) é suficiente para o MVP | Upgrade para Firebase Blaze (pay-per-use) necessário | [ ] |
| A-005 | Scraping de páginas públicas da Caixa não viola os termos de uso | Risco legal — consultar termos oficiais e limitar rate | [ ] |
| A-006 | Cloud Run Jobs consegue coletar todos os imóveis de uma UF dentro de 1 hora | Job timeout ou volume maior que esperado — particionamento necessário | [ ] |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Específico: quem (investidores), o quê (perdem oportunidades), por quê (portais dispersos, sem alertas) |
| Users | 3 | Três personas com roles e pain points claros |
| Goals | 3 | MUSTs/SHOULDs/COULDs priorizados com critério de MVP explícito |
| Success | 2 | Critérios mensuráveis presentes; volume de usuários e uptime não quantificados (sem dados reais ainda) |
| Scope | 3 | 8 features explicitamente fora do escopo com fase de retorno definida |
| **Total** | **14/15** | Acima do mínimo (12/15) — Ready for Design |

---

## Open Questions

| # | Questão | Impacto no Design | Urgência |
|---|---------|------------------|----------|
| OQ-001 | Como o usuário conecta o Telegram? (token gerado no dashboard, deep link, ou código via bot?) | Define fluxo de onboarding e modelo de dados do `telegram_chat_id` | Alta — resolver no /design |
| OQ-002 | A Caixa exige rotação de user-agent, cookies ou CAPTCHA? | Define se Playwright (com browser headless) é necessário ou se requests simples bastam | Alta — validar antes do build |
| OQ-003 | Qual o modelo de monetização? (freemium, assinatura, etc.) | Pode afetar features de auth (planos, cotas de alertas) | Baixa — pode entrar no Fase 2 |
| OQ-004 | Frequência de coleta: 3x/dia é suficiente ou usuários precisam de atualização a cada hora? | Define custo de Cloud Run Jobs e estrutura de scheduling | Média — validar com primeiros usuários |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-05-26 | define-agent | Initial version — extraído do BRAINSTORM_MVP_FASE1_CAIXA.md |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_MVP_FASE1_CAIXA.md`
