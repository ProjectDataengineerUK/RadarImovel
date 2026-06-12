# DEFINE: V2 — Melhor do Mercado + Céu Azul + Painel Admin

> Elevar o Radar Imóvel à paridade com os líderes do mercado (Smart Leilões, Auket, Núcleo),
> somar os diferenciais céu azul que ninguém tem, expandir as fontes ao máximo (leiloeiros
> privados, leilões judiciais, novas bases de risco/mercado) e criar um painel admin que
> gerencia níveis de acesso — planos comerciais com feature flags e RBAC interno de equipe.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | V2_MELHOR_DO_MERCADO |
| **Date** | 2026-06-11 |
| **Author** | define-agent |
| **Input** | `docs/ANALISE_CONCORRENCIA.md` (pesquisa de mercado 2026-06-11) + decisões do usuário |
| **Status** | ✅ Shipped (2026-06-11) |
| **Clarity Score** | 13/15 |

---

## Problem Statement

O Radar Imóvel tem diferenciais técnicos prontos (7 bancos públicos, score de risco geoespacial,
pipeline event-driven), mas perde em **paridade de features** para Smart Leilões/Auket/Núcleo
(calculadora de viabilidade, gestão de carteira, alertas WhatsApp, 800+ fontes de leiloeiros) e
**não tem como monetizar**: não existem planos de assinatura, gating de features nem painel
administrativo — hoje qualquer usuário vê tudo, e a equipe não tem perfis de acesso.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Investidor de leilão (pessoa física) | Cliente pagante (R$ 60–190/mês de teto, conforme mercado) | Precisa de viabilidade financeira, risco e velocidade num só lugar; hoje assina 2–3 ferramentas |
| Comprador de primeira vez | Cliente freemium → conversão | Rejeita leilão por confusão (78% na Resale); precisa de jornada guiada e linguagem simples |
| Assessoria / grupo de investidores | Cliente de tier alto | Precisa colaborar, exportar dados e analisar volume |
| Admin do Radar (fundador) | Operador do negócio | Não consegue criar planos, liberar features por plano nem dar acesso restrito à equipe |
| Equipe interna (operador/suporte) | Staff | Precisa acessar painel sem poder alterar planos/configurações críticas |

---

## Goals

Organizados em 4 frentes (workstreams). Prioridade MoSCoW:

### WS1 — Painel Admin & Níveis de Acesso (habilitador de tudo)

| Priority | Goal |
|----------|------|
| **MUST** | CRUD de **planos comerciais** no painel admin: nome, preço exibido, feature flags e limites quantitativos (nº de watchlists, alertas/dia, relatórios due diligence/mês, latência de alerta, export, API) |
| **MUST** | **Entitlements enforcement**: middleware no backend nega feature/limite fora do plano; frontend esconde/bloqueia UI com call-to-action de upgrade |
| **MUST** | Atribuição **manual** de plano a usuário pelo admin (ativar/desativar/expirar assinatura) — sem gateway de pagamento |
| **MUST** | **RBAC interno**: papéis `admin`, `operador`, `suporte` com permissões distintas sobre rotas administrativas; usuário comum não acessa nada de admin |
| **MUST** | **Auditoria**: toda ação administrativa registrada (quem, o quê, quando, valor anterior/novo) |
| **SHOULD** | Dashboard admin de métricas: usuários por plano, conversão, alertas enviados, saúde dos conectores |

### WS2 — Paridade competitiva ("o melhor de tudo que existe")

| Priority | Goal |
|----------|------|
| **MUST** | **Calculadora de viabilidade** por imóvel: custos de arrematação (ITBI, cartório por estado, leiloeiro, desocupação), ROI, TIR, payback e simulação venda vs. aluguel (paridade Auket/Smart) |
| **MUST** | **Busca por mapa interativo** com filtros avançados (20+ critérios) e raio geográfico (paridade Núcleo/Auket; Leaflet já está na stack) |
| **MUST** | **Alertas WhatsApp e push** além do Telegram/e-mail (camada de notificação já abstraída) |
| **SHOULD** | **Export Excel/CSV** das buscas (paridade Núcleo Premium) |
| **SHOULD** | **IA de matrícula**: extração estruturada da matrícula em PDF (paridade Smart/Arremata.ai; reusar pipeline Gemini do edital) |
| **SHOULD** | **Gestão de carteira (Kanban)**: do interesse → arremate → reforma → revenda (paridade Smart/Auket) |
| **COULD** | **Colaboração**: compartilhar carteira/análises com outros usuários, divisão de cotas (paridade Auket Plus) |

### WS3 — Céu Azul (diferenciais que ninguém tem)

| Priority | Goal |
|----------|------|
| **MUST** | **Curva de desconto preditiva**: probabilidade de novo rebaixamento de preço por imóvel nos próximos 30/60/90 dias, usando o histórico `property_changes` |
| **MUST** | **"Pergunte ao edital"**: chat RAG sobre edital + matrícula do imóvel (Vertex AI Vector Search, já planejado na stack) |
| **SHOULD** | **Radar Index**: índice público mensal de deságio por região/banco (motor de SEO/autoridade) |
| **SHOULD** | **SLA de alerta < 15 min** como promessa de produto mensurável (latência exposta no alerta: "detectado há X min") |
| **SHOULD** | **Score de revenda hiperlocal**: preço m² de mercado por bairro cruzado com o preço do leilão → lucro provável |
| **COULD** | **Modo primeira compra**: jornada guiada passo a passo com IA explicando cada etapa do imóvel específico |
| **COULD** | **API B2B / data feed** para fundos e assessorias (chave de API gerida no painel admin como feature de plano) |
| **COULD** | **Marketplace de serviços** (advogado/despachante/desocupação por comissão) |

### WS4 — Máximo de fontes

| Priority | Goal |
|----------|------|
| **MUST** | Generalizar `BankConnector` → **`SourceConnector`** (bancos, leiloeiros, tribunais usam o mesmo pipeline de normalização/dedup/alertas) |
| **MUST** | **Top 5 leiloeiros privados** conectados (Portal Zuk, Mega Leilões, Sodré Santoro, Fidalgo, Frazão — validar ToS/robots de cada um) |
| **SHOULD** | **+10 leiloeiros** seguintes por volume (meta: cobrir ~80% do volume nacional de imóveis bancários extrajudiciais) |
| **SHOULD** | **Leilões judiciais**: editais de hasta pública dos principais TJs (SP, RJ, MG primeiro) |
| **SHOULD** | **Novas bases de risco/mercado**: DataJud/CNJ (processos por imóvel/comarca), portais de anúncio para preço m² (fonte a validar juridicamente), ITBI/IPTU municipais onde houver dado aberto |
| **COULD** | Cobertura long-tail de leiloeiros regionais (caminho para os "800 leiloeiros" dos concorrentes) |

---

## Success Criteria

- [ ] Admin cria um plano novo com feature flags e o gating reflete no frontend e na API **sem deploy** (config em banco)
- [ ] 100% das rotas de API sensíveis cobertas por verificação de entitlement (teste automatizado de matriz plano × feature)
- [ ] Usuário `suporte` não consegue alterar planos (403 + registro de auditoria)
- [ ] Calculadora cobre custos de cartório/ITBI dos **27 estados** (paridade Smart Leilões)
- [ ] ≥ **15 fontes ativas** no total (7 bancos + ≥5 leiloeiros + ≥3 outras) com taxa de sucesso de coleta ≥ 95% por semana
- [ ] Latência mediana novo-imóvel → alerta **< 15 min** (vs. ciclo diário dos concorrentes)
- [ ] Curva preditiva com acerto direcional ≥ 70% em backtest no histórico de `property_changes`
- [ ] "Pergunte ao edital" responde com citação da cláusula-fonte em ≥ 90% das respostas (sem alucinação não citada)
- [ ] Alertas entregues em 4 canais: Telegram, e-mail, WhatsApp, push

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Admin cria plano | Admin logado no painel | Cria plano "Pro" com flag `risk_score=true`, `alerts_per_day=50` | Plano persiste; usuário atribuído ao Pro vê score de risco e é bloqueado no 51º alerta do dia |
| AT-002 | Gating no backend | Usuário Free (sem flag `export`) | Chama `GET /properties/export` | API responde 403 com código `PLAN_LIMIT`, frontend mostra CTA de upgrade |
| AT-003 | RBAC interno | Usuário com papel `suporte` | Tenta `PUT /admin/plans/{id}` | 403; tentativa registrada na auditoria |
| AT-004 | Atribuição manual | Admin no painel de usuários | Atribui plano "Premium" com expiração 2026-12-31 | Usuário ganha acesso imediato; após a data, sistema rebaixa para Free automaticamente |
| AT-005 | Auditoria | Admin altera preço exibido de um plano | Salva alteração | Registro com user_id, campo, valor antigo/novo e timestamp consultável no painel |
| AT-006 | Calculadora | Imóvel da Caixa em SP com preço R$ 300k | Usuário abre a calculadora | Custos de ITBI/cartório de SP pré-preenchidos; ROI/TIR/payback calculados; simulação aluguel disponível |
| AT-007 | Novo conector leiloeiro | Conector Zuk implementado | Job de coleta roda | Imóveis normalizados no mesmo schema, deduplicados contra base existente (mesmo imóvel via banco e leiloeiro = 1 registro com 2 ofertas) |
| AT-008 | Curva preditiva | Imóvel com 3 reduções históricas de preço | Usuário abre o imóvel | Card "probabilidade de queda em 30/60/90 dias" com % e base histórica explicada |
| AT-009 | Pergunte ao edital | Imóvel com edital processado | Usuário pergunta "quem paga dívidas de condomínio?" | Resposta cita o trecho/cláusula do edital; se a informação não existe, responde "não consta no edital" |
| AT-010 | Alerta multicanal | Usuário Premium com WhatsApp configurado | Novo imóvel casa com a watchlist | Alerta chega no WhatsApp e Telegram em < 15 min da detecção, com link |
| AT-011 | Dedup multi-fonte | Mesmo imóvel publicado pela Caixa e por leiloeiro parceiro | Ambas as coletas rodam | 1 imóvel com 2 fontes/preços visíveis, alerta emitido 1 vez |

---

## Out of Scope

- **Gateway de pagamento** (Stripe/Mercado Pago): checkout, webhooks, renovação e inadimplência ficam para feature dedicada — aqui só a estrutura de planos/assinaturas com ativação manual
- **Crédito embutido / originação de financiamento** (visão de longo prazo)
- **Operação própria de assessoria/desocupação** (modelo Monitor Leilão) — no máximo marketplace por comissão, e mesmo este é COULD
- **App mobile nativo** (web responsivo + push web cobrem o MVP)
- **Curso/comunidade** (modelo Smart Leilões/Arremata.ai)
- Cobertura completa de leilões judiciais de todos os TJs (começa com SP/RJ/MG)

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Técnica | Reusar schema/pipeline existentes (`properties`, `property_changes`, connectors, Pub/Sub) | `SourceConnector` é evolução do `BankConnector`, não rewrite |
| Técnica | WhatsApp exige API oficial (Meta Cloud API) com custo por conversa e aprovação de templates | Iniciar registro cedo; Telegram permanece canal default |
| Legal | Coleta de leiloeiros privados e portais de anúncio depende de ToS/robots.txt de cada fonte | Gate jurídico por fonte antes de ativar conector; fontes públicas governamentais sem restrição |
| Legal | Dados pessoais (LGPD) em processos judiciais/DataJud | Armazenar apenas dados do imóvel/processo, não das partes |
| Recurso | Equipe de 1 dev + agentes | Workstreams encadeados em ondas no /design; MUSTs primeiro |
| Custo | Gemini/Vertex (RAG + matrícula) e WhatsApp cobrados por uso | Limites por plano (entitlements) também controlam custo variável |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `app/` (backend), `frontend/` (Next.js), `jobs/` (novos conectores), `infra/terraform/` | Estrutura existente do monorepo |
| **KB Domains** | GCP serverless, FastAPI/SQLAlchemy, Next.js, prompts Gemini | Padrões já usados nas Fases 1–3 |
| **IaC Impact** | Novos recursos: schedulers por fonte nova, tópico/assinatura para canal WhatsApp, Vector Search (RAG), possivelmente Memorystore para rate-limit de entitlements | Terraform já modular (`setproduct` por fonte) |

Pontos de integração com o existente:

- `users` ganha relação com `subscriptions`/`plans` (novas tabelas) e `role` (RBAC)
- `app/api/middleware/auth.py` estende para carregar entitlements e papel
- `CONNECTOR_REGISTRY` evolui para fontes não-bancárias
- Score de risco e due diligence PDF viram features gated por plano (hoje abertos)

---

## Data Contract (novas fontes)

### Source Inventory

| Source | Type | Volume estimado | Freshness alvo | Risco de acesso |
|--------|------|-----------------|----------------|-----------------|
| Portal Zuk, Mega, Sodré, Fidalgo, Frazão | Scraping HTML/API | ~10–45k imóveis somados | 2–4×/dia | Médio (ToS por fonte) |
| TJs (SP/RJ/MG) — hasta pública | Scraping/editais PDF | ~5–15k/ano | Diário | Baixo (dado público) |
| DataJud / CNJ | API pública | Consulta sob demanda | Semanal | Baixo |
| Portais de anúncio (preço m²) | A validar juridicamente | Agregado por bairro | Mensal | Alto — gate jurídico |
| ITBI/IPTU municipais (dados abertos) | CSV/API | Capitais com dado aberto | Mensal | Baixo |

### Schema Contract (núcleo, já existente — extensões)

| Column | Type | Constraints | PII? |
|--------|------|-------------|------|
| `source_type` | VARCHAR | NOT NULL (`bank` / `auctioneer` / `court`) | Não |
| `offers[]` (nova) | tabela filha | imóvel 1—N ofertas (fonte, preço, modalidade, data) | Não |
| `plans` / `subscriptions` / `roles` / `audit_log` | novas tabelas | FKs para `users` | `audit_log` referencia user_id |

### Freshness SLAs

| Layer | Target | Measurement |
|-------|--------|-------------|
| Coleta bancos | ≤ 4h entre publicação e ingestão | timestamp fonte vs. `created_at` |
| Coleta leiloeiros | ≤ 6h | idem |
| Alerta | < 15 min após detecção | Pub/Sub publish → notificação enviada |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | ToS dos 5 leiloeiros top permitem coleta automatizada (ou há API/parceria viável) | Reduz lista de fontes MUST; priorizar próximos da fila | [ ] |
| A-002 | Histórico de `property_changes` já tem volume para treinar a curva preditiva | Lançar como heurística (regras das etapas da Caixa) e evoluir para ML | [ ] |
| A-003 | Tabelas de custo de cartório/ITBI dos 27 estados são compiláveis de fontes públicas | Lançar com 10 estados de maior volume e completar | [ ] |
| A-004 | WhatsApp Business API aprovada para o caso de uso de alertas | Lançar com Telegram/e-mail/push; WhatsApp entra depois | [ ] |
| A-005 | Dedup multi-fonte (mesmo imóvel via banco + leiloeiro) é resolvível por endereço+matrícula | Sem isso, base duplica e alertas repetem — `deduplicator` precisa de upgrade robusto | [ ] |
| A-006 | Firebase Auth comporta claims de papel/plano sem migração de auth | Camada de sessão própria no backend | [ ] |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Gap competitivo + ausência de monetização, especificado por concorrente |
| Users | 3 | 5 personas com dores distintas, incluindo admin/staff |
| Goals | 3 | 4 workstreams com MoSCoW completo |
| Success | 2 | Métricas numéricas, mas algumas dependem de baseline a medir (ex.: backtest preditivo) |
| Scope | 2 | Out of scope explícito; amplitude grande exige ondas no /design |
| **Total** | **13/15** | |

---

## Open Questions

1. Quais leiloeiros entram no top 5 definitivo? (proposta: Zuk, Mega, Sodré, Fidalgo, Frazão — confirmar por volume real e viabilidade de coleta no /design)
2. Nomes e preços dos planos iniciais (proposta da análise: Free / ~R$ 49–79 / ~R$ 149–199) — pode ser decidido no admin já que planos são configuráveis
3. Push: Web Push (FCM) basta no MVP ou exigimos push mobile (depende de app — fora de escopo)?

Nenhuma bloqueia o /design — todas têm proposta default.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-11 | define-agent | Versão inicial a partir de `docs/ANALISE_CONCORRENCIA.md` + decisões do usuário (acessos = ambos; sem gateway; fontes = leiloeiros + risco/mercado + judiciais) |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_V2_MELHOR_DO_MERCADO.md`
