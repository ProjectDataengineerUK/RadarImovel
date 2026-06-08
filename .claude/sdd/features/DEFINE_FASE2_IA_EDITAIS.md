# DEFINE: Fase 2 — IA nos Editais

> Pipeline assíncrono que lê PDFs de editais da Caixa com Gemini 2.0 Flash, extrai 13 campos estruturados e enriquece o score de oportunidade de 2 sinais para 8+.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FASE2_IA_EDITAIS |
| **Date** | 2026-06-08 |
| **Author** | define-agent |
| **Status** | Ready for Design |
| **Clarity Score** | 13/15 |
| **Precondition** | MVP Fase 1 deployado: coleta Caixa, Cloud SQL, Pub/Sub, GCS e Telegram funcionando |

---

## Problem Statement

O score de oportunidade atual (`app/agents/score_agent.py`) usa apenas dois sinais — desconto percentual e status de ocupação da planilha XLSX — e ignora informações críticas que determinam se um imóvel é uma oportunidade real ou uma armadilha financeira: dívidas herdáveis (IPTU, condomínio), ônus registrados em cartório, situação real de ocupação e data do leilão. Essas informações existem nos PDFs de editais, cuja URL (`Property.edital_url`) já é coletada, mas nenhum pipeline as processa hoje.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Comprador de imóveis em leilão | Usuário final da plataforma | Recebe alertas de imóveis com score alto mas não sabe que há R$ 40k de dívida IPTU que o arrematante herda; perde dinheiro por falta de informação |
| Investidor imobiliário | Usuário avançado | Precisa avaliar risco real rapidamente; hoje precisa baixar e ler o edital manualmente para cada imóvel de interesse |
| Operador da plataforma | Administrador | Suporte a usuários que reclamam de score "enganoso"; custo de reputação quando score não reflete risco real |

---

## Goals (MoSCoW)

| Priority | Goal |
|----------|------|
| **MUST** | Baixar o PDF do edital de `Property.edital_url` e armazená-lo no GCS |
| **MUST** | Extrair os 13 campos estruturados do edital via Gemini 2.0 Flash com `response_schema` Pydantic |
| **MUST** | Persistir os campos extraídos em `Document.ai_summary` (JSON) e atualizar `Property.risk_level` |
| **MUST** | Re-calcular `Property.opportunity_score` com 8+ sinais substituindo o cálculo atual de 2 sinais |
| **MUST** | Processar editais de forma assíncrona em job separado sem bloquear o pipeline de coleta |
| **MUST** | Garantir idempotência: re-processar o mesmo edital não duplica registros nem re-envia alertas |
| **MUST** | Adicionar migration 002 com campos de controle de status do processamento em `documents` |
| **SHOULD** | Exibir os campos extraídos no card do imóvel no dashboard (seção "Edital") |
| **SHOULD** | Enriquecer o alerta Telegram com dívidas estimadas, risco e data do leilão |
| **SHOULD** | Imóvel sem edital processado ainda exibe score básico (graceful degradation) |
| **SHOULD** | Log estruturado de `extraction_confidence` por edital para monitoramento de qualidade |
| **COULD** | Alerta de billing no GCP quando custo de Vertex AI ultrapassar 80% do budget mensal |
| **COULD** | Endpoint de administração `POST /admin/reprocess-edital/{property_id}` para re-extração manual |

---

## Success Criteria

- [ ] 95% dos editais com URL válida processados com `processing_status = done` em até 30 minutos da criação da propriedade
- [ ] `extraction_confidence >= 0.75` em pelo menos 80% das extrações (medido nas primeiras 100 execucoes reais)
- [ ] Score enriquecido usa no mínimo 4 sinais distintos quando edital disponivel (vs. 2 sinais atuais)
- [ ] Custo de inferência Vertex AI inferior a R$ 50/mês para volume de até 10.000 editais/mês
- [ ] Zero duplicação de registros `Document` para o mesmo `property_id` + `document_type=edital`
- [ ] Imóveis sem edital continuam exibindo score básico sem erro no dashboard (graceful degradation)
- [ ] Latência de processamento por edital inferior a 60 segundos (P95) em execução normal do job
- [ ] Pipeline tolera falha de URL (HTTP 404/timeout) sem derrubar o job — status `skipped` após 3 tentativas

---

## Acceptance Tests

| ID | Cenário | Given | When | Then |
|----|---------|-------|------|------|
| AT-001 | Extração com sucesso em edital padrão | `Property` com `edital_url` válida, `Document` inexistente | Job `process_editais` executa | `Document` criado com `processing_status=done`, `ai_summary` contém JSON com pelo menos 8 campos preenchidos, `Property.risk_level` atualizado |
| AT-002 | Idempotência em re-execução | `Property` com `Document` existente no status `done` | Job executa novamente para o mesmo `property_id` | Nenhum novo `Document` criado; `Property.opportunity_score` não alterado; nenhum evento Pub/Sub publicado |
| AT-003 | Graceful degradation sem edital | `Property` sem `edital_url` (campo nulo) | Rota `GET /properties/{id}` chamada pelo dashboard | Resposta 200 com `opportunity_score` calculado pelos 2 sinais básicos; campo `edital_processed=false` no response |
| AT-004 | Falha de URL do edital | `Property.edital_url` retorna HTTP 404 | Job tenta download 3 vezes com backoff | `Document.processing_status = skipped`; `processing_error` preenchido com mensagem; job continua sem crash |
| AT-005 | Score enriquecido com dívida alta | Edital com `total_debt_estimate = R$ 60.000` (>20% do `appraisal_value`) | Job processa e re-calcula score | `Property.opportunity_score` reduzido em relação ao score básico; `risk_level = high` |
| AT-006 | Score enriquecido com imóvel livre e FGTS | Edital com `occupancy_detail=livre` e `payment_modalities` inclui `fgts` | Job processa | `opportunity_score` aumentado vs. score básico; `risk_level = low` |
| AT-007 | Alerta Telegram enriquecido | `Property` processada com edital, usuário com watchlist ativa | Novo imóvel detectado na coleta | Mensagem Telegram inclui dívidas estimadas, `risk_level` e data do leilão além dos campos da Fase 1 |
| AT-008 | Migration 002 aplicada sem regressão | Banco de dados com schema Fase 1 | `alembic upgrade head` executado | Campos `processing_status`, `processing_error`, `processed_at`, `extraction_confidence` existem em `documents`; dados existentes preservados |

---

## Requisitos Não-Funcionais

| Atributo | Requisito | Justificativa |
|----------|-----------|---------------|
| **Custo** | Vertex AI < R$ 50/mês para 10k editais | Budget do MVP — Gemini 2.0 Flash ~$0.0004/edital + GCS ~$0.10/mês |
| **Latência** | Processamento assíncrono; P95 < 60s/edital | Não bloqueia coleta; usuário vê score enriquecido em minutos, não horas |
| **Idempotência** | Re-execução do job não duplica dados | Jobs Cloud Run podem ser re-executados pelo scheduler; essencial para operação confiável |
| **Degradação graciosa** | Sistema operacional sem edital processado | Coleta pode ser mais rápida que processamento; score básico sempre disponível |
| **Confiabilidade** | 3 tentativas com backoff exponencial para falhas de rede | Editais da Caixa podem ter indisponibilidade temporária |
| **Observabilidade** | Log estruturado (structlog) com `property_id`, `processing_status`, `extraction_confidence`, `duration_ms` | Permite monitorar qualidade de extração e detectar regressões |
| **Segurança** | Credenciais Vertex AI via Secret Manager; PDF armazenado em GCS com IAM restrito | Consistente com padrão de segurança da Fase 1 |
| **Compatibilidade** | Migration Alembic idempotente; rollback seguro com `downgrade` | Requisito operacional para deployments GCP |

---

## Escopo

### In Scope (Fase 2)

- Job `jobs/process_editais.py` — download de PDF, upload GCS, chamada Gemini, persistência
- Schema Pydantic `EditaisExtraction` com os 13 campos e validadores
- Migration Alembic 002 com campos de controle em `documents`
- `app/agents/score_agent.py` atualizado com função de score enriquecido (8+ sinais)
- Tópico Pub/Sub `edital-events` para orquestrar o processamento
- Terraform para novo tópico Pub/Sub e permissões Vertex AI no service account do job
- Seção "Edital" no card do imóvel no dashboard (`frontend/app/imoveis/[id]/`)
- Alerta Telegram enriquecido com campos do edital
- Editais da **Caixa** exclusivamente

### Out of Scope (Fase 2)

- Document AI (OCR dedicado) — descartado pelo brainstorm; over-engineered para editais com texto nativo
- RAG sobre corpus de editais (pgvector / Vertex AI Vector Search) — Fase 4
- Editais de outros bancos (BB, BRB, BNB, BASA, Banrisul, Banestes) — cada banco tem formato distinto; Fase 3
- Fine-tuning de modelo Gemini — sem dataset anotado; injustificado no MVP
- Notificação de "edital atualizado" (diff entre versões) — requer versionamento de extrações; pós-Fase 2
- Comparação de dívidas com dados externos (Receita Federal, cartório) — Fase 4
- Extração de fotos do edital — fotos já vêm da planilha XLSX da Fase 1
- Busca semântica sobre editais no dashboard — Fase 4
- Endpoint público para download do PDF do edital pelo usuário final

---

## Dependências Técnicas

### Dependências Internas (Fase 1 como pré-condição)

| Componente | Estado | Dependência |
|------------|--------|-------------|
| `Property.edital_url` | Preenchido pelo `collect_caixa.py` | URL de entrada do pipeline |
| `Document` model (SQLAlchemy) | Existe com `gcs_path`, `extracted_text`, `ai_summary` | Recebe novos campos via migration 002 |
| `Property.risk_level` (String 20) | Campo reservado desde Fase 1 | Recebe `low / medium / high` |
| `Property.opportunity_score` | Calculado pelo `score_agent.py` atual | Substituído pelo score enriquecido |
| Cloud Storage bucket `radar-imovel-docs` | Provisionado via Terraform Fase 1 | Prefix `/editais/` adicionado |
| Padrão Cloud Run Job | Consolidado com `collect_caixa.py` e `process_alerts.py` | Novo job segue o mesmo padrão |
| Pub/Sub `property-events` | Operacional na Fase 1 | `alert_agent.py` já o consome; sem mudança |
| `alert_agent.py` | Operacional na Fase 1 | Consome `property-events`; só formatar mensagem enriquecida |

### Dependências Externas (Novas na Fase 2)

| Serviço | Propósito | Terraform necessário |
|---------|-----------|---------------------|
| Vertex AI (Gemini 2.0 Flash) | Extração estruturada dos PDFs | IAM: `roles/aiplatform.user` para SA do job |
| Pub/Sub tópico `edital-events` | Orquestrar download + processamento de editais | Novo recurso `google_pubsub_topic` |
| GCS prefix `gs://radar-imovel-docs/editais/` | Armazenar PDFs dos editais | Sem novo bucket; apenas nova convenção de path |

### Novas Dependências Python (`pyproject.toml`)

| Pacote | Extra | Uso |
|--------|-------|-----|
| `google-cloud-aiplatform` | `job` | SDK Vertex AI para chamada Gemini |
| `google-cloud-storage` | já em uso | Upload do PDF; sem mudança |

---

## Data Contract

### Campos extraídos pelo Gemini (Document.ai_summary — JSON)

| Campo | Tipo | Obrigatório | Notas |
|-------|------|-------------|-------|
| `edital_number` | `string \| null` | Não | Número do edital (ex: "0001234-2026") |
| `auction_date_1st` | `YYYY-MM-DD \| null` | Não | Data da primeira praça/leilão |
| `auction_date_2nd` | `YYYY-MM-DD \| null` | Não | Data da segunda praça (se houver) |
| `minimum_bid_1st` | `Decimal \| null` | Não | Lance mínimo primeira praça (R$) |
| `minimum_bid_2nd` | `Decimal \| null` | Não | Lance mínimo segunda praça (R$) |
| `appraisal_value` | `Decimal \| null` | Não | Valor de avaliação oficial (R$) |
| `payment_modalities` | `list[string]` | Sim (pode ser vazio) | `["vista", "financiamento_caixa", "fgts", "carta_credito"]` |
| `occupancy_detail` | `enum` | Sim | `livre \| ocupado_com_acao_judicial \| ocupado_sem_acao \| locado \| unknown` |
| `encumbrances` | `list[Encumbrance]` | Sim (pode ser vazio) | Lista de ônus: `{type, amount_approx, description}` |
| `total_debt_estimate` | `Decimal \| null` | Não | Soma estimada das dívidas herdáveis (R$) |
| `registration_number` | `string \| null` | Não | Matrícula do imóvel no cartório |
| `auctioneer_name` | `string \| null` | Não | Nome do leiloeiro responsável |
| `risk_flags` | `list[string]` | Sim (pode ser vazio) | `["ocupado", "divida_elevada", "onus_registrado", "area_irregular"]` |
| `risk_level` | `enum` | Sim | `low \| medium \| high` — calculado pelo Gemini com base nos campos |
| `extraction_confidence` | `float [0.0–1.0]` | Sim | Grau de confiança do Gemini na extração |

### Campos de controle adicionados à tabela `documents` (Migration 002)

| Coluna | Tipo | Default | Valores válidos |
|--------|------|---------|-----------------|
| `processing_status` | `VARCHAR(20)` | `pending` | `pending \| processing \| done \| failed \| skipped` |
| `processing_error` | `TEXT` | NULL | Mensagem de erro ou stack trace truncado |
| `processed_at` | `TIMESTAMPTZ` | NULL | Timestamp do término do processamento |
| `extraction_confidence` | `NUMERIC(3,2)` | NULL | Espelho do campo no JSON `ai_summary` |

### Freshness SLA

| Evento | SLA | Medição |
|--------|-----|---------|
| `Property` com `edital_url` criada | Edital processado em até 30 minutos | `processed_at - first_seen_at` |
| Job `process_editais` executado | Todos os `pending` do lote processados em até 10 minutos | Duração do Cloud Run Job |

### Completeness

- 100% dos registros `Document` com `processing_status=done` têm `ai_summary` com JSON válido
- Zero registros com `extraction_confidence` NULL quando `processing_status=done`
- Zero `property_id` duplicados na tabela `documents` para `document_type=edital`

---

## Fluxo de Dados (Fase 2)

```text
[Cloud Scheduler] → [Pub/Sub: collect-trigger]
        |
[Cloud Run Job: collect_caixa.py] (sem mudança)
        |
    Property criada/atualizada com edital_url preenchida
        |
[Pub/Sub: edital-events] {property_id, edital_url, bank_id}
        |
[Cloud Run Job: process_editais.py] (NOVO)
    1. Verifica Document existente — se done, encerra (idempotência)
    2. Cria/atualiza Document com processing_status=processing
    3. Download PDF via requests(edital_url, timeout=30s, retries=3)
    4. Upload GCS: gs://radar-imovel-docs/editais/{bank}/{state}/{property_id}.pdf
    5. Chama Vertex AI: gemini.generate_content([pdf_uri], response_schema=EditaisExtraction)
    6. Pydantic: EditaisExtraction.model_validate(response.parsed)
    7. Atualiza Document: ai_summary=json, processing_status=done, processed_at=now
    8. Re-calcula Property.opportunity_score + risk_level (score_agent enriquecido)
    9. Publica property-events {type: "edital_processed", property_id}
        |
[alert_agent.py] (sem mudança de lógica; formata mensagem enriquecida se campos disponíveis)
        |
[Telegram Bot] — alerta enriquecido com dívidas, risco e data do leilão
```

---

## Arquitetura de Arquivos (Novos e Modificados)

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `jobs/process_editais.py` | CRIAR | Entrypoint do novo Cloud Run Job |
| `app/agents/score_agent.py` | MODIFICAR | Score enriquecido com 8+ sinais |
| `app/connectors/caixa/edital_extractor.py` | CRIAR | Lógica de extração Gemini + schema Pydantic `EditaisExtraction` |
| `migrations/versions/002_edital_processing.py` | CRIAR | Migration com campos de controle em `documents` |
| `infra/terraform/pubsub.tf` | MODIFICAR | Adicionar tópico `edital-events` |
| `infra/terraform/iam.tf` | MODIFICAR | `roles/aiplatform.user` para SA do job |
| `infra/terraform/cloud_run.tf` | MODIFICAR | Novo job `process_editais` |
| `frontend/app/imoveis/[id]/page.tsx` | MODIFICAR | Seção "Edital" no card do imóvel |
| `app/api/routes/properties.py` | MODIFICAR | Incluir campos do edital no response |
| `tests/unit/test_edital_extractor.py` | CRIAR | Testes unitários com PDF fixture |
| `tests/integration/test_process_editais.py` | CRIAR | Testes de integração com mock Vertex AI |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `jobs/`, `app/connectors/caixa/`, `app/agents/`, `migrations/versions/`, `infra/terraform/`, `frontend/app/imoveis/[id]/` | Segue estrutura existente da Fase 1 |
| **KB Domains** | `prompt-engineering/patterns/document-extraction`, `pydantic/patterns/extraction-schema`, `pydantic/patterns/llm-output-validation`, `gcp/patterns/event-driven-pipeline`, `genai/concepts/tool-calling`, `data-modeling/patterns/schema-migration`, `testing/patterns/integration-tests` | Padrões diretamente aplicáveis |
| **IaC Impact** | Modificar recursos existentes + novo tópico Pub/Sub | `pubsub.tf` (novo tópico), `iam.tf` (nova binding Vertex AI), `cloud_run.tf` (novo job) |

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Schema `Document` existente sem os campos de controle | Requer migration 002 antes de qualquer execução do job |
| Technical | `Property.risk_level` é `String(20)` — deve aceitar `low/medium/high` | Sem migration necessária; campo já existe e aceita os valores |
| Technical | Gemini 2.0 Flash via Vertex AI; sem Document AI | Abordagem A do brainstorm; PDFs escaneados degradam graciosamente |
| Cost | Budget de Vertex AI: < R$ 50/mês | Limitar tamanho do lote de editais por execução de job; usar Gemini Flash (não Pro) |
| Operational | Jobs Cloud Run são re-executados pelo scheduler | Idempotência obrigatória via verificação de `processing_status=done` antes de processar |
| Scope | Apenas editais da Caixa (Fase 2) | Formato de edital de outros bancos varia; conector por banco na Fase 3 |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | Editais da Caixa são PDFs com texto nativo (não imagem escaneada) na maioria dos casos | Gemini teria qualidade inferior de extração em PDFs de imagem; `extraction_confidence` baixa; precisaria Document AI | [ ] Validar com amostra de 10 PDFs reais |
| A-002 | `Property.edital_url` é preenchido pelo `collect_caixa.py` de forma confiável antes do job de editais executar | Job encontraria propriedades sem URL; processaria 0 editais; precisaria ajustar o coletor | [ ] Confirmar com execução real do coletor |
| A-003 | Vertex AI Gemini 2.0 Flash aceita URI do GCS diretamente como input multimodal sem upload separado via File API | Precisaria de etapa extra de upload via File API antes da inferência; aumenta complexidade | [ ] Confirmar com teste de PoC antes do /design |
| A-004 | Custo de R$ 50/mês cobre 10.000 editais/mês com Gemini Flash | Orçamento insuficiente se volume crescer acima de 100k editais/mês | [ ] Calcular com pricing atual do Vertex AI |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3/3 | Problema concreto com código-fonte identificado (`score_agent.py`), impacto financeiro real para o usuário, campos ausentes nomeados |
| Users | 3/3 | Tres personas com roles e pain points especificos; comprador, investidor e operador |
| Goals | 3/3 | MoSCoW completo com 7 MUST, 4 SHOULD, 2 COULD; todos mensuráveis ou verificáveis |
| Success | 2/3 | 8 critérios com métricas numéricas; A-001 e A-003 ainda não validados influenciam 2 dos critérios |
| Scope | 2/3 | In/out scope explícito com 13 itens excluídos; fronteira com Fase 3 clara; uma incerteza menor sobre momento do trigger (abaixo) |
| **Total** | **13/15** | Acima do limiar de 12/15; pronto para Design |

**Minimum to proceed: 12/15** — aprovado.

---

## Open Questions

Apenas 2 questões abertas menores, que o /design pode resolver sem bloquear a implementação:

| # | Questão | Opções | Decisão Recomendada | Impacto se Errar |
|---|---------|--------|---------------------|-----------------|
| OQ-01 | **Trigger do job**: quando publicar a mensagem `edital-events`? | (a) `collect_caixa.py` publica durante a coleta ao detectar `edital_url` preenchida; (b) job separado varre `documents WHERE processing_status='pending'` a cada N minutos | Opção (a): menor latência, acoplamento mínimo via Pub/Sub já usado; (b) mais simples de implementar sem mudança no coletor | Opção (b) adiciona até N minutos de latência; opção (a) requer 3 linhas no coletor existente |
| OQ-02 | **Modelo Gemini**: 2.0 Flash vs. 1.5 Pro | Flash: menor custo (6x), maior throughput, latência menor; Pro: maior precisão em PDFs complexos | Iniciar com Flash; fallback manual para Pro via config se `extraction_confidence < 0.60` em produção | Flash com confiança baixa → score incorreto; mitigado pelo campo `extraction_confidence` que permite triagem manual |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-08 | define-agent | Versão inicial a partir de BRAINSTORM_FASE2_IA_EDITAIS.md |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_FASE2_IA_EDITAIS.md`

**Antes do /design, ação humana recomendada (A-001 e A-003):**
1. Baixar 5–10 PDFs de editais reais da Caixa (variar UF e modalidade: leilão extrajudicial, venda direta, licitação aberta) e confirmar se são texto nativo ou imagem escaneada.
2. Executar PoC de 10 linhas confirmando que `vertexai.generative_models.Part.from_uri(gcs_uri, mime_type="application/pdf")` funciona sem File API separada.
   Esses dois pontos validam A-001 e A-003 e evitam retrabalho no /design.
