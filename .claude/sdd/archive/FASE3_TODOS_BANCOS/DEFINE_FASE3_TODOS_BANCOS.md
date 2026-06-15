# DEFINE: Fase 3 — Conectores de Todos os Bancos

> Cobertura completa dos bancos públicos brasileiros: BB, BRB, BNB, BASA, Banrisul e Banestes no mesmo pipeline de coleta, normalização e alerta da Fase 1.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FASE3_TODOS_BANCOS |
| **Date** | 2026-06-08 |
| **Author** | define-agent |
| **Status** | Ready for Design |
| **Clarity Score** | 13/15 |
| **Source** | BRAINSTORM_FASE3_TODOS_BANCOS.md |

---

## Problem Statement

A plataforma Radar Imóvel monitora apenas a Caixa Econômica Federal (Fase 1). O mercado de leilões e vendas diretas de imóveis bancários inclui outros seis bancos públicos — Banco do Brasil, BRB, Banco do Nordeste, Banco da Amazônia, Banrisul e Banestes — que representam dezenas de milhares de imóveis adicionais. Investidores que usam a plataforma perdem oportunidades nesses bancos. A Fase 3 fecha essa lacuna, trazendo todos os bancos para o mesmo pipeline de coleta, detecção de mudanças, score e alertas.

---

## Target Users

| User | Pain Point Endereçado |
|------|-----------------------|
| Investidor que já usa Radar Imóvel | Quer ver imóveis do BB e BNB no mesmo painel sem acessar múltiplos sites |
| Investidor no Nordeste | Quer alertas do BNB (maior banco regional) além da Caixa |
| Investidor no DF/entorno | Quer imóveis do BRB que aparecem via Resale |
| Novo usuário | Percebe que a plataforma cobre todos os principais bancos, não apenas a Caixa |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Implementar `BankConnector` para BB com coleta paginada do portal `www49.bb.com.br` |
| **MUST** | Implementar `BankConnector` para BNB com coleta via Playwright + portlet Liferay |
| **MUST** | Implementar `BankConnector` para BRB com Playwright + network interception da API Resale |
| **MUST** | Implementar `BankConnector` para BASA com coleta de editais PDF alimentando pipeline de IA |
| **MUST** | Implementar `BankConnector` para Banestes com coleta de editais PDF |
| **MUST** | Implementar `BankConnector` para Banrisul após descoberta e validação da URL correta |
| **MUST** | Criar `collect_bb.py`, `collect_brb.py`, `collect_bnb.py`, `collect_basa.py`, `collect_banrisul.py`, `collect_banestes.py` seguindo o padrão de `collect_caixa.py` |
| **MUST** | Cada normalizer mapeia campos do banco para o schema `Property` comum |
| **MUST** | Todos os imóveis novos disparam evento Pub/Sub `property-events` (tipo `new`) |
| **MUST** | Todos os imóveis com mudança disparam evento Pub/Sub `property-events` (tipo `changed`) |
| **MUST** | Imóveis BASA/Banestes com edital PDF disparam evento `property-editais` para pipeline de IA |
| **SHOULD** | Banco de dados populado com `Bank` records para cada novo banco |
| **SHOULD** | Terraform atualizado com Cloud Run Jobs e Cloud Schedulers para os 6 novos bancos |
| **SHOULD** | Testes unitários para cada parser e normalizer |
| **COULD** | Painel de admin exibe status de coleta por banco (BB, BRB, BNB, etc.) |

---

## Requisitos Funcionais por Banco

### Banco do Brasil (BB)

| ID | Requisito |
|----|-----------|
| RF-BB-01 | O `BBConnector.discover_sources()` retorna a lista de URLs paginadas do portal `https://www49.bb.com.br/appbb/portal/bb/imob/` para todos os tipos de modalidade (licitação aberta, fechada, venda direta) |
| RF-BB-02 | O `BBConnector.fetch_raw()` realiza request `httpx` com headers de browser (User-Agent, Accept-Language, Referer) e retorna o HTML da página |
| RF-BB-03 | Se `httpx` receber status 403 ou resposta vazia, o fallback é Playwright simples (sem stealth Radware) |
| RF-BB-04 | O `BBParser.parse()` extrai de cada card/linha de imóvel: código do imóvel, tipo, endereço, cidade, UF, preço de venda, valor de avaliação, modalidade, situação de ocupação e link do edital |
| RF-BB-05 | O `BBNormalizer.normalize()` mapeia campos BB para o schema `Property`: `external_code` = número do processo, `sale_modality` = modalidade normalizada, `discount_percent` calculado se ausente |
| RF-BB-06 | O job `collect_bb.py` executa paginação: continua até receber página vazia ou `page > MAX_PAGES` |
| RF-BB-07 | O job `collect_bb.py` aceita env var `MODALITY` para coletar apenas uma modalidade (ex: `LICITACAO_ABERTA`) |

### BRB — Banco de Brasília

| ID | Requisito |
|----|-----------|
| RF-BRB-01 | O `BRBConnector.discover_sources()` retorna uma única URL base da Resale para BRB: `https://www.resale.com.br/banco-brb` |
| RF-BRB-02 | O `BRBConnector.fetch_raw()` usa Playwright para navegar na página Resale BRB, aguardar o React renderizar os cards de imóveis e interceptar a resposta JSON da API interna da Resale (via `page.on("response", ...)`) |
| RF-BRB-03 | Se a interceptação de network retornar JSON válido com lista de imóveis, `fetch_raw` retorna esses bytes JSON |
| RF-BRB-04 | Se a interceptação falhar, o fallback é extração de HTML dos cards após renderização completa |
| RF-BRB-05 | O `BRBParser.parse()` desserializa o JSON da API Resale (ou parseia HTML de cards) extraindo: código, tipo, endereço, cidade/UF/bairro, preço, desconto, modalidade, link |
| RF-BRB-06 | O `BRBNormalizer.normalize()` mapeia campos Resale/BRB para o schema `Property` |
| RF-BRB-07 | O job `collect_brb.py` itera todas as páginas disponíveis da listagem BRB na Resale |

### Banco do Nordeste (BNB)

| ID | Requisito |
|----|-----------|
| RF-BNB-01 | O `BNBConnector.discover_sources()` retorna a URL da página `https://www.bnb.gov.br/bens-a-venda` com parâmetro de estado e página |
| RF-BNB-02 | O `BNBConnector.fetch_raw()` usa Playwright para carregar a página, aguardar o portlet Liferay renderizar a tabela de imóveis (aguardar seletor CSS do portlet ou `networkidle`) e retornar o HTML do portlet |
| RF-BNB-03 | O `BNBParser.parse()` extrai de cada linha da tabela HTML: número do lote, tipo, cidade/UF, valor de avaliação, valor de venda, modalidade, situação, link do edital PDF |
| RF-BNB-04 | O `BNBNormalizer.normalize()` mapeia campos BNB para o schema `Property` |
| RF-BNB-05 | O job `collect_bnb.py` aceita env var `ESTADO` (UF de 2 letras) e itera páginas de resultados para aquele estado |
| RF-BNB-06 | Se o portlet não renderizar em 30 segundos, o job registra erro e continua com o próximo estado |

### Banco da Amazônia (BASA)

| ID | Requisito |
|----|-----------|
| RF-BASA-01 | O `BASAConnector.discover_sources()` retorna URLs das páginas de comunicados/transparência do site `https://www.bancoamazonia.com.br` onde editais de alienação são publicados |
| RF-BASA-02 | O `BASAConnector.fetch_raw()` usa Playwright (ou `httpx` se a página for estática) para navegar na seção de comunicados e extrair links de PDFs de editais de leilão/alienação identificados por título ou classificação |
| RF-BASA-03 | Para cada PDF novo (não visto antes — verificado por hash URL ou nome), `fetch_raw` faz download do PDF e retorna seus bytes |
| RF-BASA-04 | O `BASAParser.parse()` cria `RawProperty` com `raw_data = {"edital_pdf_bytes": base64(bytes), "edital_url": url}` por edital — um `RawProperty` por PDF, não um por imóvel (a extração de imóveis é responsabilidade do pipeline de IA) |
| RF-BASA-05 | O job `collect_basa.py` publica evento no tópico `property-editais` para cada novo PDF de edital detectado, com `{"edital_url": url, "bank_code": "basa", "raw_gcs_path": "gs://..."}` |
| RF-BASA-06 | O job `collect_basa.py` persiste um registro de `Document` no banco com status `pending` para o edital descoberto |
| RF-BASA-07 | Editais já processados (status `done` ou `processing`) não são re-enviados ao pipeline |

### Banrisul

| ID | Requisito |
|----|-----------|
| RF-BRS-01 | Antes da implementação, a URL correta do portal de imóveis do Banrisul deve ser descoberta e validada por acesso manual (via browser) e documentada em `app/connectors/banrisul/collector.py` como constante `BANRISUL_LIST_URL` |
| RF-BRS-02 | O `BanrisulConnector.discover_sources()` retorna a lista de URLs do portal, podendo ser paginado |
| RF-BRS-03 | O `BanrisulConnector.fetch_raw()` usa `httpx` com headers de browser para requests .aspx (WebForms); se ViewState for necessário, usa Playwright |
| RF-BRS-04 | O `BanrisulParser.parse()` extrai de tabelas HTML: código do imóvel, tipo, endereço, cidade/RS, preço, modalidade, link |
| RF-BRS-05 | O `BanrisulNormalizer.normalize()` mapeia campos Banrisul para o schema `Property` |
| RF-BRS-06 | O job `collect_banrisul.py` segue o padrão `collect_caixa.py` |

### Banestes

| ID | Requisito |
|----|-----------|
| RF-BES-01 | O `BanestesConnector.discover_sources()` retorna a URL da seção de publicações/editais do site `https://www.banestes.com.br` onde editais de alienação são publicados |
| RF-BES-02 | O `BanestesConnector.fetch_raw()` usa `httpx` para acessar a página de publicações e extrair links de editais PDF com palavras-chave "alienação", "leilão", "imóvel" no título ou na URL |
| RF-BES-03 | Para cada PDF novo, `fetch_raw` faz download e retorna bytes |
| RF-BES-04 | O `BanestesParser.parse()` cria `RawProperty` por edital PDF, similar ao BASA (RF-BASA-04) |
| RF-BES-05 | O job `collect_banestes.py` publica evento `property-editais` para cada novo edital PDF descoberto |
| RF-BES-06 | Editais já processados não são re-enviados |

---

## Critérios de Aceite Mensuráveis

| ID | Critério | Como Medir |
|----|----------|------------|
| CA-BB-01 | O coletor BB extrai pelo menos 100 imóveis na primeira execução | Verificar `stats["collected"] >= 100` no log do job |
| CA-BB-02 | Nenhum imóvel duplicado inserido em execuções consecutivas | `content_hash` único verificado; `SELECT COUNT(*) FROM properties WHERE bank_code = 'bb'` não cresce sem novas licitações |
| CA-BRB-01 | O coletor BRB extrai todos os imóveis da Resale BRB em uma execução | Comparar contagem com total mostrado na interface Resale ± 5% |
| CA-BNB-01 | O coletor BNB cobre todos os 9 estados do Nordeste + DF | Log do job confirma iteração por CE, PE, BA, MA, PI, RN, PB, AL, SE, DF |
| CA-BNB-02 | Imóvel do BNB aparece no painel em menos de 4 horas após a coleta | Timestamp de `created_at` vs timestamp do alerta |
| CA-BASA-01 | Novo edital PDF do BASA é detectado em até 7 dias após publicação | Job semanal deve capturar editais publicados na semana anterior |
| CA-BASA-02 | Edital BASA detectado dispara evento `property-editais` no mesmo run | Verificar Pub/Sub publish count após execução do job |
| CA-BRS-01 | URL do Banrisul documentada e validada antes do início do coding | Constante `BANRISUL_LIST_URL` presente e URL retorna 200 em teste manual |
| CA-BRS-02 | O coletor Banrisul extrai pelo menos 10 imóveis | Verificar `stats["collected"] >= 10` no log |
| CA-BES-01 | Edital Banestes detectado em até 7 dias após publicação | Job semanal |
| CA-GERAL-01 | Falha no coletor de um banco não afeta os coletores dos outros bancos | Cada job é independente; falha de `collect_bb.py` não impacta `collect_bnb.py` |
| CA-GERAL-02 | Arquivo bruto (HTML ou PDF) de cada banco salvo no GCS a cada execução | `gs://{bucket}/raw/{bank_code}/{data}/{arquivo}` criado e não vazio |
| CA-GERAL-03 | Imóvel novo de qualquer banco gera alerta Telegram em watchlist correspondente | Criar watchlist para SP/BB, coletar, confirmar recebimento de mensagem Telegram |

---

## Acceptance Tests

| ID | Cenário | Dado | Quando | Então |
|----|---------|------|--------|-------|
| AT-BB-01 | Coleta paginada BB | Banco BB com 5.000 imóveis no portal | `collect_bb.py` executa | `stats["collected"] >= 1000`; arquivo HTML de cada página salvo no GCS; imóveis com `bank_code = "bb"` em `properties` |
| AT-BB-02 | Fallback Playwright para BB | Portal BB retorna 403 para `httpx` | `collect_bb.py` executa com `httpx` bloqueado | Playwright executa e coleta imóveis; log indica `"bb.httpx_blocked"` + `"bb.playwright_ok"` |
| AT-BRB-01 | Network interception Resale | Resale carrega listagem BRB | `collect_brb.py` executa | Playwright intercepta chamada à API Resale e salva JSON; `stats["collected"] >= 50` |
| AT-BNB-01 | Coleta por estado BNB | `ESTADO=CE` definido | `collect_bnb.py` executa | Imóveis do Ceará coletados; portlet aguardado com sucesso; `stats["collected"] > 0` |
| AT-BNB-02 | Timeout do portlet BNB | Portlet Liferay não carrega em 30s | `collect_bnb.py` executa para estado específico | Log de `"bnb.portlet_timeout"`; job continua para próximo estado sem crash |
| AT-BASA-01 | Detecção de novo edital BASA | Novo PDF de edital de alienação publicado no site BASA | `collect_basa.py` executa | PDF baixado para GCS; evento publicado em `property-editais`; `Document` criado com `status = "pending"` |
| AT-BASA-02 | Edital já processado não reenviado | Edital X com `status = "done"` | `collect_basa.py` executa novamente | Edital X não reenviado ao Pub/Sub; log indica `"basa.edital_already_processed"` |
| AT-BRS-01 | URL Banrisul válida | `BANRISUL_LIST_URL` configurado e acessível | `collect_banrisul.py` executa | Request retorna HTTP 200; pelo menos 1 imóvel extraído |
| AT-BES-01 | Detecção de edital Banestes | Nova publicação de edital no site Banestes | `collect_banestes.py` executa | PDF detectado, baixado, evento publicado em `property-editais` |
| AT-GERAL-01 | Imóvel BB aparece no painel | `collect_bb.py` insere novo imóvel | Usuário acessa o painel web | Imóvel com `bank_code = "bb"` visível na tabela filtrável |
| AT-GERAL-02 | Alerta Telegram multi-banco | Usuário tem watchlist: RJ, qualquer banco, ≤ R$500k | Imóvel novo no RJ detectado no BB | Alerta Telegram enviado com `banco = "Banco do Brasil"` e dados do imóvel |

---

## Escopo In / Out

### In Scope (Fase 3)

- Connectors: `BBConnector`, `BRBConnector`, `BNBConnector`, `BASAConnector`, `BanrisulConnector`, `BanestesConnector`
- Parsers e normalizers correspondentes para cada banco
- Jobs: `collect_bb.py`, `collect_brb.py`, `collect_bnb.py`, `collect_basa.py`, `collect_banrisul.py`, `collect_banestes.py`
- Banco de dados: inserção dos 6 novos `Bank` records via migration Alembic
- GCS: upload de arquivos brutos por banco (`raw/bb/`, `raw/brb/`, etc.)
- Pub/Sub: eventos `property-events` (new/changed) e `property-editais` (para BASA/Banestes) já existentes na Fase 2
- Terraform: 6 novos Cloud Run Jobs + 6 novos Cloud Schedulers
- Testes: unitários para cada parser e normalizer
- Painel web: filtro por banco já existente no schema — sem alteração de frontend necessária
- Alertas: o `AlertAgent` já filtra por `bank_code` na watchlist — sem alteração necessária

### Out of Scope (Fase 3)

| Feature | Fase |
|---------|------|
| Página de detalhe do imóvel com fotos para BB/BRB | Fase 3.5 / Fase 4 |
| Score de oportunidade específico por banco (ex: liquidez regional) | Fase 4 |
| Mapa de calor de oportunidades por banco | Fase 4 |
| Extração de dados estruturados de editais BASA/Banestes via IA | Fase 2 (pipeline existente) — conector apenas dispara o evento |
| API pública para desenvolvedores consultarem imóveis por banco | Não planejado |
| Scraping de licitações judiciais (não bancárias) | Fora do escopo do produto |
| Monitoramento em tempo real (webhook / push) | Fora do escopo — polling é suficiente |

---

## Dependências

| Dependência | Tipo | Responsável | Status |
|------------|------|-------------|--------|
| `BankConnector` interface em `app/connectors/base.py` | Técnica | Fase 1 | Existente |
| `Property` model + schema em `migrations/` | Técnica | Fase 1 | Existente |
| Pipeline de editais (`process_editais` job) | Técnica | Fase 2 | Existente |
| Tópico Pub/Sub `property-editais` | Técnica | Fase 2 | Existente |
| `EditalExtractor` (`app/connectors/caixa/edital_extractor.py`) | Técnica | Fase 2 | Existente |
| Records `Bank` para BB, BRB, BNB, BASA, Banrisul, Banestes no banco | Dados | Fase 3 | Pendente — migration ou seed |
| URL correta do portal Banrisul (descoberta manual) | Descoberta | Time | Pendente |
| Acesso manual ao portal BB para validar HTML de listagem | Validação | Time | Pendente |
| Playwright instalado no `Dockerfile.job` | Infra | Fase 1 | Existente (dependência opcional) |

---

## Constraints

| Tipo | Constraint | Impacto |
|------|-----------|---------|
| Técnico | Nenhum banco tem API pública — scraping obrigatório para todos | Todos os conectores exigem Playwright ou `httpx` robusto |
| Técnico | Portal BRB bloqueado por F5 WAF — acesso apenas via Resale | BRBConnector depende de terceiro (Resale) |
| Técnico | URL Banrisul não confirmada (lançamento recente abr/2026) | Implementação de Banrisul bloqueada até validação manual |
| Operacional | BASA e Banestes têm dados apenas em PDF — sem listagem estruturada | Não é possível garantir campos completos sem pipeline de IA (Fase 2) |
| Legal | Scraping de portais públicos de bancos federais para fins informativos é legalmente permitido no Brasil (dados públicos) | Nenhum impedimento legal identificado |
| Custo | Cada banco adiciona ~10–30 Cloud Run execuções/mês | Custo incremental estimado: < R$10/mês por banco |

---

## Modelo de Dados — Sem Alterações Necessárias

O schema `properties` da Fase 1 já suporta múltiplos bancos via `bank_id`. Os campos são agnósticos ao banco:

```
properties:
  external_code     → número do processo/imóvel de cada banco
  bank_id           → FK para banks.id (novo registro por banco)
  title             → descrição do imóvel
  property_type     → tipo normalizado
  address, city, state, neighborhood
  appraisal_value, minimum_value, current_value, discount_percent
  occupancy_status  → normalizado: "Ocupado" / "Desocupado" / "Não informado"
  sale_modality     → string livre normalizada por banco
  official_url      → URL do imóvel ou da busca
  edital_url        → URL do PDF do edital (se disponível)
  opportunity_score → calculado pelo score_agent existente
  status            → "active" / "inactive"
  content_hash      → SHA-256 do conteúdo para deduplicação
```

Migration necessária apenas para inserir novos records em `banks`:

```sql
INSERT INTO banks (code, name, active) VALUES
  ('bb', 'Banco do Brasil', true),
  ('brb', 'BRB - Banco de Brasília', true),
  ('bnb', 'Banco do Nordeste do Brasil', true),
  ('basa', 'Banco da Amazônia', true),
  ('banrisul', 'Banrisul', true),
  ('banestes', 'Banestes', true);
```

---

## Estrutura de Arquivos a Criar

```
app/connectors/
  bb/__init__.py, collector.py, parser.py, normalizer.py
  brb/__init__.py, collector.py, parser.py, normalizer.py
  bnb/__init__.py, collector.py, parser.py, normalizer.py
  basa/__init__.py, collector.py, parser.py, normalizer.py
  banrisul/__init__.py, collector.py, parser.py, normalizer.py
  banestes/__init__.py, collector.py, parser.py, normalizer.py

jobs/
  collect_bb.py
  collect_brb.py
  collect_bnb.py
  collect_basa.py
  collect_banrisul.py
  collect_banestes.py

migrations/versions/
  002_add_fase3_banks.py  (seed dos 6 novos Bank records)

tests/unit/
  test_bb_parser.py, test_bb_normalizer.py
  test_brb_parser.py, test_brb_normalizer.py
  test_bnb_parser.py, test_bnb_normalizer.py
  test_basa_parser.py, test_basa_normalizer.py
  test_banrisul_parser.py, test_banrisul_normalizer.py
  test_banestes_parser.py, test_banestes_normalizer.py

infra/terraform/
  cloud_run_fase3.tf     (6 novos Cloud Run Jobs)
  scheduler_fase3.tf     (6 novos Cloud Schedulers)
```

---

## Frequência de Coleta por Banco

| Banco | Cron (UTC) | Justificativa |
|-------|-----------|---------------|
| BB | `0 8,14,20 * * *` (3x/dia) | Alto volume, licitações com datas específicas |
| BRB | `0 9,15 * * 1,3,5` (3x/semana) | Baixo volume, Resale atualiza semanalmente |
| BNB | `0 9,15 * * 1,3,5` (3x/semana) | Médio volume, ciclo de licitações quinzenal |
| BASA | `0 10 * * 1` (1x/semana, segunda) | Muito baixo volume, publicações mensais |
| Banrisul | `0 9,15 * * 2,5` (2x/semana) | Baixo volume |
| Banestes | `0 10 * * 3` (1x/semana, quarta) | Muito baixo volume, publicações esporádicas |

---

## Campos Mínimos Obrigatórios por Banco

Para que o `opportunity_score` seja calculado (requer pelo menos `current_value` e `city`):

| Campo | BB | BRB | BNB | BASA | Banrisul | Banestes |
|-------|----|----|-----|------|----------|---------|
| `external_code` | Via portal | Via Resale | Via portlet | Via edital + IA | Via portal | Via edital + IA |
| `city` + `state` | Sim | Sim | Sim | Via IA | Sim | Via IA |
| `current_value` | Sim | Sim | Sim | Via IA | Sim | Via IA |
| `appraisal_value` | Sim | Sim | Sim | Via IA | Se disponível | Via IA |
| `sale_modality` | Sim | Sim | Sim | Via IA | Sim | Via IA |
| `official_url` | Sim | Via Resale | Sim | URL do edital | Sim | URL do edital |

Bancos que dependem de extração via IA (BASA, Banestes) terão `opportunity_score = null` até o pipeline de IA processar o edital.

---

## Clarity Score

| Dimensão | Nota | Justificativa |
|----------|------|---------------|
| Problema claramente definido | 1/1 | Bancos sem cobertura identificados com precisão |
| Usuário-alvo identificado | 1/1 | Investidores segmentados por banco/região |
| Goals priorizados (MUST/SHOULD/COULD) | 1/1 | Tabela completa com prioridades |
| Critérios de aceite mensuráveis | 1/1 | Métricas quantitativas por banco |
| Acceptance tests escritos | 1/1 | AT por banco + cenários de fallback |
| Escopo In/Out documentado | 1/1 | Tabela clara com justificativas |
| Dependências listadas com status | 1/1 | Todas identificadas incluindo bloqueantes |
| Constraints documentadas | 1/1 | Técnicas, operacionais e legais |
| Modelo de dados especificado | 1/1 | Schema existente reutilizado; apenas seed de dados |
| Estrutura de arquivos mapeada | 1/1 | Todos os 24 novos arquivos listados |
| Frequência de coleta por banco | 1/1 | Cron expressions específicas |
| Sample data inventory | 0/1 | Nenhum sample disponível — coleta manual necessária antes do coding |
| Banrisul URL bloqueante documentada | 1/1 | Dependência crítica explicitada |
| **Total** | **13/15** | |

---

## Próximos Passos

1. **Antes de implementar Banrisul:** Descoberta manual da URL correta do portal de imóveis
2. **Antes de implementar BB/BNB/BRB:** Captura de amostras reais via Playwright manual (1 página de listagem cada)
3. **Implementação em ordem de prioridade:** BB → BNB → BRB → Banrisul → BASA → Banestes
4. **Agente recomendado:** `@python-developer` para implementar os 6 conectores
5. **Após implementação:** `@python-reviewer` para revisão dos conectores
6. **Infra:** `@gcp-data-architect` para provisionar os 6 novos jobs + schedulers no Terraform
