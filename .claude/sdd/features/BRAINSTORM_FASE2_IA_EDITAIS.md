# BRAINSTORM: Fase 2 — IA nos Editais (Radar Imóvel)

> Sessão exploratória para clarificar abordagem antes de capturar requisitos formais

## Metadata

| Atributo | Valor |
|----------|-------|
| **Feature** | FASE2_IA_EDITAIS |
| **Data** | 2026-06-08 |
| **Autor** | brainstorm-agent |
| **Status** | Ready for Define |
| **Precondição** | MVP Fase 1 deployado (Caixa, FastAPI, Cloud SQL, Pub/Sub, GCS, Telegram) |

---

## Problema Central

O score de oportunidade atual do Radar Imóvel é calculado com apenas dois sinais:

```python
# app/agents/score_agent.py — estado atual
score = min(discount_percent, max_points) + occupancy_bonus
```

Esse score ignora informações críticas que determinam se um imóvel é realmente uma boa
oportunidade ou uma armadilha financeira:

- Dívidas acumuladas (IPTU em atraso, condomínio, hipotecas) que o arrematante herda
- Situação real de ocupação (livre, ocupado, litigioso)
- Ônus registrados em cartório que travam a transferência
- Prazo e condições de pagamento (financiamento FGTS, à vista, carta de crédito)
- Valor de avaliação real vs. valor mínimo de leilão (desconto verdadeiro)
- Data e leiloeiro responsável (urgência, credibilidade)

Todas essas informações estão nos **editais** — PDFs publicados pela Caixa junto de cada imóvel.
O modelo `Document` já existe no schema com `extracted_text` e `ai_summary` reservados para
esta fase. A URL do edital já é coletada em `Property.edital_url`. A fundação está pronta;
falta o pipeline de processamento.

---

## Contexto Técnico Existente

| Componente | Estado atual | Impacto na Fase 2 |
|-----------|-------------|-------------------|
| `Property.edital_url` | Preenchido pela Caixa | URL de download já disponível |
| `Document.gcs_path` | Schema pronto, sem dados | Apenas inserir o PDF baixado |
| `Document.extracted_text` | Campo `Text` reservado | Recebe output do pipeline de extração |
| `Document.ai_summary` | Campo `Text` reservado | Recebe JSON estruturado do Gemini |
| `Property.risk_level` | Campo `String(20)` reservado | Recebe `low / medium / high` calculado |
| `Property.opportunity_score` | Cálculo básico (desconto + ocupação) | Score enriquecido substitui este |
| `Cloud Storage` | Já em uso para XLSX brutos | Bucket separado ou prefix `/editais/` |
| `Cloud Run Jobs` | Padrão consolidado no projeto | Novo job `process_editais.py` |
| `Pub/Sub` | Mensageria central do projeto | Novo tópico `edital-events` |

---

## Abordagens Exploradas

### Abordagem A: Gemini Direto com PDF Nativo (multimodal) — Recomendada

**O que é:**
Baixar o PDF do edital, salvar no GCS, e enviar diretamente para o Gemini 1.5 Pro / 2.0 Flash
usando a File API do Vertex AI. O Gemini lê o PDF como input multimodal (sem OCR separado)
e retorna os campos estruturados via chamada com `response_schema` (JSON Schema forçado).
Sem Document AI, sem etapa de OCR separada.

**Fluxo:**
```text
Property.edital_url
        ↓
[Job: process_editais.py] — download PDF → GCS (editais/{bank}/{uf}/{property_id}.pdf)
        ↓
[Vertex AI Files API] — upload GCS URI como parte da mensagem
        ↓
[Gemini 1.5 Pro / 2.0 Flash] — prompt estruturado + response_schema Pydantic
        ↓
[EditaisExtraction (Pydantic)] — validação automática dos campos
        ↓
[Document.ai_summary = JSON] + [Property.risk_level + opportunity_score atualizados]
        ↓
[Pub/Sub: edital-events] → alert_agent já existente reusa a infra
```

**Pros:**
- Pipeline mais simples: 1 serviço GCP, sem Document AI
- Gemini 1.5 Pro suporta PDFs de até 1.000 páginas como input nativo
- `response_schema` do Vertex AI garante JSON estruturado sem parsing frágil
- Custo mais baixo que Document AI para volume de editais da Caixa (~R$ 0,01–0,05/edital)
- Time-to-MVP mais rápido: semanas, não meses
- Editais com texto nativo (a maioria da Caixa) ficam perfeitos; PDF escaneados degradam mas
  ainda funcionam via visão do Gemini
- Alinha com a escolha estratégica de Vertex AI já definida em `context.md`

**Cons:**
- PDFs muito escaneados (imagem pura) têm qualidade inferior ao Document AI com OCR dedicado
- Latência por edital: 3–15 segundos (aceitável em batch assíncrono)
- Custo por token: editais longos (>50 páginas) consomem mais tokens
- Dependência de disponibilidade do Vertex AI (SLA 99,5%)

**Custo estimado:**
- Gemini 2.0 Flash: ~$0.075/1M tokens input; edital médio ~5k tokens → ~$0.0004/edital
- 10.000 editais/mês: ~$4/mês em inferência
- GCS storage: ~$0.02/GB; 10k PDFs × 500KB = ~$0.10/mês

**Confiança:** 0.90 — abordagem alinhada com KB `prompt-engineering/patterns/document-extraction`
e `genai/concepts/rag-architecture`, stack GCP já consolidada no projeto.

---

### Abordagem B: Document AI (OCR) + Gemini (interpretação)

**O que é:**
Pipeline em dois estágios: Document AI processa o PDF com OCR de alta qualidade e retorna
texto estruturado com coordenadas. O texto extraído é então enviado ao Gemini para
interpretação semântica e extração de campos de negócio.

**Fluxo:**
```text
PDF no GCS
    ↓
[Document AI — Form Parser / Custom Extractor]
    ↓
Texto extraído + entidades detectadas
    ↓
[Gemini Flash] — interpretação e scoring
    ↓
Campos estruturados + risk_level
```

**Pros:**
- OCR de qualidade superior para PDFs escaneados ou com layout complexo
- Document AI Custom Extractor pode ser treinado com editais reais para alta precisão
- Separação de responsabilidades: OCR vs. interpretação semântica
- Rastreabilidade: `extracted_text` salva o output do OCR separado do `ai_summary`

**Cons:**
- Dois serviços GCP para configurar, manter e pagar (Document AI + Vertex AI)
- Document AI Form Parser: ~$1.50/1.000 páginas — 10 vezes mais caro que Abordagem A
- Custom Extractor exige dataset de treinamento com editais anotados (meses de trabalho)
- Pipeline mais complexo: mais código, mais pontos de falha, mais infra Terraform
- Editais da Caixa são majoritariamente PDFs com texto nativo — OCR dedicado é over-engineering
  para o volume e tipo de documento

**Custo estimado:**
- Document AI Form Parser: $1.50/1.000 páginas; edital médio 5 páginas → $0.0075/edital
- 10.000 editais/mês: ~$75/mês só em Document AI (18x mais caro que Abordagem A)
- Gemini adicional: ~$4/mês

**Confiança:** 0.80 — tecnicamente válida, mas over-engineered para o estágio atual do produto.

---

### Abordagem C: RAG sobre editais (Vector Search)

**O que é:**
Processar todos os editais em chunks, gerar embeddings via Vertex AI Embeddings e armazenar
no Vertex AI Vector Search (ou pgvector no Cloud SQL já existente). Usuários ou agentes podem
fazer perguntas semânticas sobre qualquer edital: "Quais imóveis têm dívidas de IPTU acima de
R$ 10.000?" ou "Imóveis livres de ônus em São Paulo".

**Fluxo:**
```text
PDF → Texto → Chunks (512 tokens, 10% overlap) → Embeddings → pgvector
                                                                   ↓
                                             Query semântica ← Dashboard
                                                                   ↓
                                             Gemini responde com citação de trecho
```

**Pros:**
- Busca semântica poderosa sobre o corpus completo de editais
- Responde perguntas abertas que campos estruturados não cobrem
- pgvector já está disponível no Cloud SQL PostgreSQL (sem novo serviço)
- Habilita funcionalidades premium diferenciadas

**Cons:**
- Complexidade muito maior: chunking, embedding pipeline, vector store, inference pipeline
- Problema do MVP: usuários ainda não conhecem o produto, volume de editais é baixo
- RAG resolve "perguntas abertas" — mas os campos específicos (IPTU, ônus, data do leilão)
  são melhor extraídos de forma estruturada via Abordagem A
- Custo de embeddings e latência de busca adicionam complexidade operacional
- Segundo o KB `ai-data-engineering/concepts/rag-pipelines`: RAG se justifica quando há
  necessidade de respostas sobre corpus grande e perguntas não antecipáveis — não é o caso
  no MVP da Fase 2

**Custo estimado:**
- Vertex AI Embeddings: ~$0.025/1M tokens; razoável
- Vertex AI Vector Search: mínimo $65/mês (índice dedicado) — muito caro para MVP
- pgvector alternativo: sem custo adicional, mas sem escalabilidade para Fase 4

**Confiança:** 0.75 — tecnicamente correto para Fase 4; prematuro para Fase 2 MVP.

---

## Abordagem Selecionada

| Atributo | Valor |
|----------|-------|
| **Escolhida** | Abordagem A — Gemini Direto com PDF Nativo |
| **Raciocínio** | Pipeline mínimo, custo baixo, stack GCP já consolidada, editais da Caixa são majoritariamente PDF com texto nativo, `response_schema` do Vertex AI garante output estruturado sem parsing frágil |
| **KB Domains aplicáveis no /define** | `prompt-engineering/patterns/document-extraction`, `pydantic/patterns/extraction-schema`, `gcp/patterns/event-driven-pipeline`, `genai/concepts/tool-calling` |

---

## Campos a Extrair dos Editais

Baseado na análise dos tipos de edital da Caixa (leilão extrajudicial, venda direta,
licitação aberta) e no que impacta diretamente o score de oportunidade:

### Campos Estruturados (JSON extraído pelo Gemini)

```json
{
  "edital_number": "string | null",
  "auction_date_1st": "YYYY-MM-DD | null",
  "auction_date_2nd": "YYYY-MM-DD | null",
  "minimum_bid_1st": "number | null",
  "minimum_bid_2nd": "number | null",
  "appraisal_value": "number | null",
  "payment_modalities": ["vista", "financiamento_caixa", "fgts", "carta_credito"],
  "occupancy_detail": "livre | ocupado_com_acao_judicial | ocupado_sem_acao | locado | unknown",
  "encumbrances": [
    {
      "type": "iptu | condominio | hipoteca | outros",
      "amount_approx": "number | null",
      "description": "string"
    }
  ],
  "total_debt_estimate": "number | null",
  "registration_number": "string | null",
  "auctioneer_name": "string | null",
  "auctioneer_contact": "string | null",
  "risk_flags": ["ocupado", "divida_elevada", "onus_registrado", "area_irregular"],
  "risk_level": "low | medium | high",
  "extraction_confidence": "0.0–1.0"
}
```

### Como os campos afetam o score

| Campo | Impacto no score | Direção |
|-------|-----------------|---------|
| `total_debt_estimate` | Reduz o desconto efetivo | Negativo se > 10% do valor |
| `occupancy_detail` | Substitui o `occupancy_status` da planilha com dado mais preciso | Positivo se `livre` |
| `risk_flags` | Penalidade por flag identificada | Negativo (-5 a -20 pontos por flag) |
| `payment_modalities` inclui `fgts` | Aumenta pool de compradores | Positivo (+5 pontos) |
| `extraction_confidence` | Peso da contribuição dos dados do edital | Proporcional |

### Score enriquecido (Fase 2)

```python
# Substituição do score_agent.py atual
score = (
    discount_score(discount_percent, total_debt_estimate, appraisal_value)  # 0–50
    + occupancy_score(occupancy_detail)                                       # 0–20
    + payment_score(payment_modalities)                                       # 0–10
    + risk_penalty(risk_flags)                                                # −50 a 0
    + edital_confidence_weight(extraction_confidence)                         # fator de ajuste
)
```

---

## Fluxo de Dados Completo (Fase 2)

```text
[Cloud Scheduler] → [Pub/Sub: collect-trigger]
        ↓
[Cloud Run Job: collect_caixa.py] (já existente)
        ↓
    detecta Property.edital_url preenchido E Document sem gcs_path
        ↓
[Pub/Sub: edital-download-trigger] — mensagem com {property_id, edital_url}
        ↓
[Cloud Run Job: process_editais.py] (NOVO)
    1. Download do PDF via requests (edital_url da Caixa)
    2. Upload para GCS: gs://radar-imovel-docs/editais/{bank}/{state}/{property_id}.pdf
    3. Insere Document(gcs_path=..., document_type="edital", status="pending")
    4. Chama Vertex AI: gemini.generate_content([pdf_part], response_schema=EditaisExtraction)
    5. Valida com Pydantic: EditaisExtraction.model_validate(response.text)
    6. Atualiza Document(extracted_text=raw, ai_summary=json_campos)
    7. Re-calcula Property.opportunity_score + risk_level
    8. Publica Pub/Sub: property-events (alert_agent já consome)
        ↓
[alert_agent.py] (já existente, sem mudança) → Telegram enriquecido
```

---

## Mudanças Necessárias no Schema (Migration 002)

O schema atual tem `Document.extracted_text` e `Document.ai_summary` como campos genéricos.
Para a Fase 2, precisamos de campos adicionais para rastrear estado do processamento:

```sql
-- Migration 002: campos de controle do pipeline de editais
ALTER TABLE documents ADD COLUMN processing_status VARCHAR(20) DEFAULT 'pending';
-- valores: pending | processing | done | failed | skipped

ALTER TABLE documents ADD COLUMN processing_error TEXT;
ALTER TABLE documents ADD COLUMN processed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE documents ADD COLUMN extraction_confidence NUMERIC(3,2);

-- Índice para job processar apenas pendentes
CREATE INDEX ix_documents_pending ON documents (processing_status)
  WHERE processing_status IN ('pending', 'failed');
```

---

## Integrações com Dashboard (Fase 2)

### Card do imóvel — seção "Edital"

```
[ EDITAL PROCESSADO ]
Leilão 1: 15/07/2026 — lance mínimo R$ 120.000
Leilão 2: 29/07/2026 — lance mínimo R$ 90.000 (se houver)
Pagamento: Vista, Financiamento Caixa, FGTS
Ocupação: Livre (confirmado no edital)
Dívidas estimadas: R$ 8.400 (IPTU: R$ 5.200 + Condomínio: R$ 3.200)
Ônus: Nenhum registrado
Risco: MEDIO  [?]
```

### Alertas Telegram — formato enriquecido

```
NOVO IMÓVEL - Radar Imóvel

Apartamento 2/4 — Fortaleza/CE
Avaliação: R$ 280.000 | Lance mín.: R$ 168.000 (40% desconto)
Edital processado: dívidas ~R$ 8.400 | ocupado sem ação judicial
Risco: MEDIO | Score: 62/100

Ver detalhes → https://radar-imovel.app/imoveis/{id}
```

---

## Decisões em Aberto (Necessitam /define)

| # | Decisão | Opções | Impacto |
|---|---------|--------|---------|
| 1 | Modelo Gemini: 1.5 Pro vs 2.0 Flash | Pro: maior precisão; Flash: menor custo e latência | Custo vs. qualidade de extração |
| 2 | Quando processar o edital? | (a) assim que Property criada; (b) sob demanda quando usuário abre o card; (c) batch noturno | Latência vs. custo |
| 3 | Retry policy para falhas de extração | Quantas tentativas? Backoff exponencial? Fila dead-letter? | Confiabilidade do pipeline |
| 4 | Score retroativo | Re-calcular score de todos os imóveis ativos quando edital chegar? | Carga no banco e notificações duplicadas |
| 5 | Exibir "edital em processamento" no dashboard | Spinner enquanto processa; ou esconder até ter dados? | UX — evitar confusão |
| 6 | Versionar extrações | Guardar múltiplas versões se edital for atualizado? | Auditoria vs. complexidade |
| 7 | Limite de custo mensal | Hard cap de tokens/mês no Vertex AI? Alert de billing? | Previsibilidade de custo |

---

## Features Removidas (YAGNI para o MVP da Fase 2)

| Feature Cogitada | Motivo para Remover | Pode Entrar Quando? |
|-----------------|---------------------|---------------------|
| RAG sobre corpus de editais | Complexidade alta, benefício incerto no volume atual | Fase 4 (Inteligência de mercado) |
| Document AI (OCR dedicado) | Over-engineered para editais com texto nativo; 18x mais caro | Se surgir volume expressivo de PDFs escaneados |
| Fine-tuning de modelo | Sem dataset anotado; custo de treinamento injustificado no MVP | Fase 3+ com dados reais acumulados |
| Comparação de dívidas com mercado | Requer integração com Receita Federal / cartório | Fase 4 |
| Extração de fotos do edital | Fora do escopo; fotos já vêm da planilha XLSX | Não prioritário |
| Notificação de "edital atualizado" | Exige diff entre versões de edital | Pós-Fase 2 |
| Leitura de editais de outros bancos | Formato varia por banco; um conector de cada vez | Fase 3 (junto com conectores dos bancos) |

---

## Inventário de Dados de Referência

| Tipo | Disponibilidade | Uso |
|------|----------------|-----|
| PDFs de editais da Caixa | Disponíveis via `edital_url` (campo já coletado) | Input do pipeline |
| Exemplos de campos extraídos | Nenhum ainda — coletar 10 editais reais para calibrar o prompt | Necessário antes do /design |
| Ground truth anotado | Nenhum | Criar manualmente com 10–20 editais para validar extração |
| Formato dos editais | Padronizado pela Caixa (template oficial) mas com variações por tipo de venda | Prompt precisa cobrir 3 tipos: leilão extrajudicial, venda direta, licitação aberta |

**Ação recomendada antes do /define:** coletar 10 PDFs de editais reais da Caixa (diferentes
UFs, diferentes modalidades) e anotar manualmente os campos para ter ground truth que calibre
o prompt do Gemini.

---

## Riscos Identificados

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Gemini extrai campos incorretos em editais mal formatados | Média | Alto (score errado) | `extraction_confidence` + revisão manual das primeiras 100 extrações |
| URL do edital muda ou fica indisponível | Baixa | Médio | Retry com backoff; status `skipped` se URL 404 persistente |
| Custo de tokens escala mais que previsto | Baixa | Médio | Billing alert no GCP; preview de custo antes do rollout |
| Editais com informações incompletas (campos ausentes) | Alta | Baixo | Pydantic com `Optional`; campos ausentes não penalizam score |
| Leitura de editais de outros bancos tem formato diferente | Certeza | Baixo agora | Conector por banco; Fase 3 resolve |

---

## KB Domains para o /define

| Domínio | Path | Relevância |
|---------|------|-----------|
| `prompt-engineering` | `patterns/document-extraction.md` | Template de extração estruturada com Pydantic |
| `prompt-engineering` | `patterns/multi-pass-extraction.md` | Se um único pass não cobrir todos os campos |
| `pydantic` | `patterns/extraction-schema.md` | Schema `EditaisExtraction` com validadores |
| `pydantic` | `patterns/llm-output-validation.md` | Retry em caso de ValidationError |
| `gcp` | `patterns/event-driven-pipeline.md` | Padrão Pub/Sub → Cloud Run Job |
| `gcp` | `patterns/gcs-triggered-workflow.md` | Alternativa: trigger por upload do PDF no GCS |
| `genai` | `concepts/tool-calling.md` | `response_schema` do Vertex AI como ferramenta |
| `data-modeling` | `patterns/schema-migration.md` | Migration 002 com campos de controle |
| `testing` | `patterns/integration-tests.md` | Testes com PDF fixtures reais |

---

## Resumo da Sessão

| Métrica | Valor |
|---------|-------|
| Abordagens Exploradas | 3 |
| Abordagem Recomendada | A — Gemini Direto (PDF nativo) |
| Features Removidas (YAGNI) | 7 |
| Decisões em Aberto para /define | 7 |
| Campos a Extrair | 13 campos estruturados |
| Custo estimado MVP | ~$4–8/mês para 10k editais |
| Confiança da Recomendação | 0.90 |

---

## Próximo Passo

**Pronto para:** `/define .claude/sdd/features/BRAINSTORM_FASE2_IA_EDITAIS.md`

**Antes do /define, ação humana recomendada:**
Baixar 10 PDFs de editais reais da Caixa (variar UF e modalidade de venda) e anotar
manualmente os 13 campos para ter ground truth. Isso garante que o prompt do /design
seja calibrado com dados reais, não hipotéticos.
