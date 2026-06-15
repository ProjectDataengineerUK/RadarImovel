# BRAINSTORM: Fase 3 — Conectores de Todos os Bancos

> Sessão exploratória para decidir estratégia de coleta por banco antes de capturar requisitos

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FASE3_TODOS_BANCOS |
| **Date** | 2026-06-08 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Contexto

Fase 1 (Caixa) e Fase 2 (IA de editais) estão implementadas. O conector Caixa estabeleceu o padrão:
- `BankConnector` abstrato com 4 métodos: `discover_sources`, `fetch_raw`, `parse`, `normalize`
- Playwright com bypass Radware (stealth mode) para contornar proteção do portal Caixa
- CSV por UF (27 arquivos) + detalhe por imóvel individual
- Cloud Run Job parametrizado por UF + Pub/Sub para eventos

A Fase 3 adiciona os 6 bancos restantes. A pergunta central é: **cada banco tem uma estratégia diferente de coleta, formato diferente e nível diferente de proteção**.

---

## Pesquisa por Banco (Findings de Campo)

### 1. Banco do Brasil (BB)

**URL do portal:** `https://www49.bb.com.br/appbb/portal/bb/imob/` (portal legado Java/.bbaction)
**URL do portal público alternativo:** `https://www.bb.com.br/pbb/pagina-inicial/imoveis` (WordPress SPA — 403 sem JS)
**Parceiro Resale:** `https://www.resale.com.br/banco-do-brasil` (React SPA, sem SSR)
**Portal de licitações:** `https://www.licitacoes-e.com.br/aop/index.jsp` (Java EE, formulário de busca)

**Formato de dados:** HTML renderizado no servidor (JSP/bbaction). Sem CSV/XLSX público. Sem API REST documentada. O portal legado `www49.bb.com.br` retorna HTML paginado com imóveis listados.

**Nível de proteção:** Médio. O `/pbb/` retorna 403 para bots. O `www49.bb.com.br` aceita requests com headers corretos. Sem Radware ou Cloudflare detectado, mas exige cookie de sessão e headers de referer.

**Campos disponíveis:** Tipo do imóvel, cidade/UF, endereço, preço de venda, valor de avaliação, modalidade (licitação aberta/fechada, venda direta), situação de ocupação, número do edital, link do edital PDF.

**Volume estimado:** Alto — BB tem presença nacional. Estimativa: 5.000–15.000 imóveis ativos.

**Frequência de atualização:** Semanal a quinzenal (licitações abertas têm datas fixas).

**Estratégia recomendada:** `httpx` com headers de browser + cookie de sessão inicial. Paginação via parâmetro GET. Parser HTML com BeautifulSoup. Se o portal bloquear, fallback para Playwright (sem stealth complexo — não é Radware).

**Evidência técnica:** O portal `www49.bb.com.br/appbb/portal/bb/imob/` retorna 83 KB de conteúdo com fontes embutidas em base64 — é um portal Java com CSS/JS inline, mas o HTML de listagem é server-rendered e parseável. O acesso ao `/pbb/` (WordPress) retorna 403, confirmando que a listagem real fica no subdomínio legado.

---

### 2. BRB — Banco de Brasília

**URL do portal:** `https://www.brb.com.br/imoveis/` — retorna "Request Rejected" (F5/BIG-IP WAF)
**Parceiro primário:** `https://www.resale.com.br/banco-brb` (Resale, React SPA)
**Parceiro secundário:** Informações de que BRB usa Resale como canal exclusivo para venda de imóveis retomados (confirmado pelo retorno "Request Rejected" na URL direta do BRB)

**Formato de dados:** Resale.com.br é uma SPA React sem SSR — o HTML retornado tem 13 KB e é apenas o shell da aplicação com scripts. Nenhum dado de imóvel em HTML estático. A Resale tem uma API interna (`api.resale.com.br`) mas não é pública e exige autenticação.

**Nível de proteção:** Alto no portal BRB direto (F5 BIG-IP WAF — pior que Radware). A Resale não tem proteção pesada no front-end mas a API interna requer tokens de sessão obtidos via login no browser.

**Campos disponíveis (via Resale):** Tipo, endereço completo, cidade/UF/bairro, preço, desconto, modalidade, fotos, link do edital, número do imóvel.

**Volume estimado:** Baixo a médio — BRB é banco regional (DF e entorno). Estimativa: 200–800 imóveis ativos.

**Frequência de atualização:** Semanal.

**Estratégia recomendada:** Playwright com sessão Resale. Navegar até `resale.com.br/banco-brb`, aguardar carregamento React, iterar cards de imóveis. Alternativa: interceptar chamadas XHR/fetch da Resale via Playwright network interception para capturar a API JSON interna. **Esta é a estratégia mais eficiente**: configurar Playwright para capturar a resposta da API interna da Resale ao navegar na página.

**Risco:** Resale pode mudar a API interna ou adicionar autenticação mais rígida.

---

### 3. Banco do Nordeste (BNB)

**URL do portal:** `https://www.bnb.gov.br/bens-a-venda` (Liferay CMS)
**Portlet Liferay:** `p_p_id=com_bnb_bens_a_venda_portlet_BensAVendaPortlet` (observado no HTML)

**Formato de dados:** Liferay portlet — o conteúdo principal carrega via JavaScript assíncrono após a página inicial. O HTML estático da página contém apenas o esqueleto Liferay. O portlet de bens-a-venda renderiza uma tabela HTML com paginação.

**Nível de proteção:** Baixo a médio. O Liferay não usa Radware/Cloudflare. Requests simples com User-Agent retornam o shell, mas o conteúdo do portlet exige a segunda requisição ao endpoint de render. Testado: o portlet direto (`/c/portal/render_portlet?p_p_id=...`) retorna 0 bytes sem cookie de sessão Liferay.

**Campos disponíveis:** Tipo do bem, localização (cidade/UF), valor de avaliação, valor de venda, modalidade, situação (ocupado/desocupado), número do processo, link do edital PDF.

**Volume estimado:** Médio — BNB atua no Nordeste (9 estados). Estimativa: 800–2.500 imóveis ativos.

**Frequência de atualização:** Quinzenal a mensal.

**Estratégia recomendada:** Playwright para carregar a página e aguardar o portlet renderizar, depois extrair HTML com BeautifulSoup. O Playwright simples (sem stealth complexo) deve ser suficiente, pois não há Radware. Alternativa mais robusta: Playwright com interceptação de network para capturar a resposta JSON do portlet.

**Nota sobre PDF:** Uma tentativa de download de PDF de relação retornou HTML — o BNB não mantém uma lista única em arquivo estático. Os dados ficam no portlet dinâmico.

---

### 4. Banco da Amazônia (BASA)

**URL do portal:** `https://www.bancoamazonia.com.br` (Next.js 14 com export estático)
**Páginas exploradas:**
- `/servicos/alienacao-de-bens` → retorna 434 KB (Next.js shell, sem conteúdo SSR sobre imóveis)
- `/servicos/leiloes` → idem
- `/transparencia/comunicados` → idem
- `/alienacao-de-bens` → idem

**Formato de dados:** O site do BASA é uma Next.js SPA com export estático. Nenhum dos paths acessados retorna dados de imóveis em HTML estático. Os dados de leilões/alienações do BASA são publicados **como editais PDF** no Diário Oficial e no próprio site na seção de comunicados/transparência.

**Nível de proteção:** Baixo. O Next.js estático não tem proteção. O desafio não é proteção, mas o formato dos dados: editais PDF sem estrutura padronizada.

**Campos disponíveis (via editais PDF):** Número do processo/edital, tipo do bem, endereço, valor de avaliação, valor mínimo de lance, modalidade, data do leilão, contato do leiloeiro.

**Volume estimado:** Muito baixo — BASA atua apenas na Amazônia Legal (9 estados, menor volume de inadimplência). Estimativa: 20–150 imóveis ativos em editais simultâneos.

**Frequência de atualização:** Baixa — publicações mensais ou bimestrais de editais.

**Estratégia recomendada:** Playwright para navegar na seção de comunicados/transparência, identificar novos PDFs de editais, fazer download e alimentar o pipeline de extração de editais da Fase 2 (Document AI + Gemini). Não há listagem estruturada — tudo passa pelo pipeline de IA.

---

### 5. Banrisul

**URL do portal:** `https://www.banrisul.com.br/bob/link/bobexw00_imoveisleilao.aspx` — retorna 404
**URL testada:** `https://www.banrisul.com.br/bob/site/link/imoveis-a-venda.html` — retorna página "Página não encontrada" (7 KB)
**robots.txt:** Confirma que `/bob/link/` existe mas alguns caminhos são bloqueados para crawlers

**Contexto importante (CLAUDE.md):** O CLAUDE.md registra que a página de bens à venda do Banrisul foi "lançada em abr/2026". O fato de todas as URLs testadas retornarem 404 ou "página não encontrada" sugere que **o portal ainda não está estável ou foi renomeado após o lançamento**.

**Formato de dados:** O Banrisul usa tecnologia XHTML 1.0 Transitional (sistema legado .NET/ASP.NET WebForms — extensão `.aspx`). O sistema legado provavelmente retorna tabelas HTML.

**Nível de proteção:** Desconhecido (não conseguimos acessar a página). O sistema legado `.aspx` tipicamente não tem proteção avançada.

**Volume estimado:** Baixo a médio — Banrisul é banco regional do Rio Grande do Sul. Estimativa: 100–500 imóveis ativos.

**Frequência de atualização:** Semanal a quinzenal.

**Estratégia recomendada:** Descoberta da URL correta primeiro (via `robots.txt`, sitemap, ou inspeção manual). Depois `httpx` simples + BeautifulSoup para páginas .aspx. Se necessário, Playwright para lidar com ViewState do WebForms.

**Dependência crítica:** Descoberta manual da URL real antes de implementar o conector.

---

### 6. Banestes

**URL testada:** `https://www.banestes.com.br/leiloes/` — retorna 404 (página criativa com CSS animado)
**URL testada:** `https://www.banestes.com.br/imoveis` — idem
**URL testada:** `https://www.banestes.com.br/nossos-servicos/leilao-de-bens` — idem

**Contexto:** O CLAUDE.md descreve o Banestes como "publicações legais e editais de alienação" — confirma que não há portal estruturado, apenas publicações em PDF/DOE.

**Formato de dados:** Editais publicados no Diário Oficial do Estado do Espírito Santo e na própria página do Banestes. Sem portal de busca. Sem CSV/XLSX.

**Nível de proteção:** Baixo — o desafio é encontrar a URL correta e os documentos PDF.

**Volume estimado:** Muito baixo — Banestes é banco estadual do Espírito Santo. Estimativa: 10–60 imóveis ativos.

**Frequência de atualização:** Muito baixa — trimestral ou conforme publicação de editais.

**Estratégia recomendada:** Monitoramento da página de comunicados/notícias do Banestes com Playwright ou `httpx`, identificando novos links de editais PDF, download e extração via pipeline de IA da Fase 2. Similar ao BASA.

---

## Tabela Comparativa de Estratégias

| Banco | Formato | Proteção | Volume | Estratégia Principal | Fallback |
|-------|---------|---------|--------|---------------------|---------|
| **BB** | HTML paginado (JSP/.bbaction) | Médio (cookie + referer) | Alto (5k–15k) | `httpx` + BeautifulSoup + paginação | Playwright simples |
| **BRB** | SPA React (Resale) | Alto (WAF F5 no site BRB) | Baixo-Médio (200–800) | Playwright + network interception Resale API | Playwright scraping de cards |
| **BNB** | Liferay portlet (HTML assíncrono) | Baixo-Médio (sem cookie) | Médio (800–2.5k) | Playwright + aguardar portlet | Playwright + BeautifulSoup |
| **BASA** | Editais PDF (Next.js estático) | Baixo | Muito Baixo (20–150) | Playwright + PDF download → pipeline IA | `httpx` + download PDF |
| **Banrisul** | HTML legado .aspx (WebForms) | Desconhecido | Baixo-Médio (100–500) | `httpx` + BeautifulSoup (URL a descobrir) | Playwright + ViewState |
| **Banestes** | Editais PDF (página HTML simples) | Baixo | Muito Baixo (10–60) | `httpx` + PDF download → pipeline IA | Playwright |

---

## Perguntas Exploradas

### Q1: Um job genérico ou um job por banco?

**Análise:**

*Opção A — Job genérico `collect_all_banks.py` parametrizado por `BANK_CODE`*
- Pros: Um único Cloud Run Job para provisionar, menos infra Terraform
- Cons: Container de ~2 GB (inclui Playwright + todas as dependências) mesmo para bancos que só precisam de `httpx`; coupling entre conectores; falha de um banco impacta o diagnóstico dos outros; scaling independente impossível

*Opção B — Um job por banco (6 novos jobs: `collect_bb`, `collect_brb`, `collect_bnb`, `collect_basa`, `collect_banrisul`, `collect_banestes`)*
- Pros: Isolamento total; imagem Docker mínima por banco; escalamento independente; Cloud Scheduler independente (BB diário, BASA semanal)
- Cons: 6 novos Dockerfiles + 6 novos jobs Terraform

*Opção C — Job genérico com imagem Playwright + connector registry*
- Pros: Uma imagem reutilizável; connector selecionado por env var `BANK_CODE`
- Cons: Mesma imagem pesada para todos os bancos; sem isolamento de falhas

**Recomendação:** Opção B (um job por banco), seguindo exatamente o padrão da Fase 1 (`collect_caixa`). O isolamento e a simplicidade operacional superam o overhead de 6 jobs adicionais no Terraform. Para bancos de baixo volume (BASA, Banestes), o scheduler pode rodar semanalmente, reduzindo custo.

**Confidence:** 0.92 — o padrão já estabelecido no codebase (`collect_caixa.py`) é um job por banco/modalidade.

---

### Q2: Como normalizar campos diferentes para o schema comum?

O schema `Property` em `migrations/versions/001_initial_schema.py` já foi projetado para ser agnóstico ao banco. O `CaixaNormalizer` demonstra o padrão: cada banco tem seu próprio `Normalizer` que mapeia campos específicos para o schema comum.

Campos que diferem por banco:
- `external_code`: BB usa número de processo judicial, BNB usa número de lote, BASA usa número de edital + sequencial
- `sale_modality`: BB tem "Licitação Aberta", "Licitação Fechada", "Venda Direta"; BNB tem "Leilão Público", "Venda Direta"; Caixa tem "Licitação Aberta", "Venda Direta"
- `official_url`: alguns bancos não têm URL por imóvel — usar URL da busca como fallback
- `discount_percent`: nem todos os bancos publicam o desconto explicitamente — calcular a partir de `(appraisal_value - current_value) / appraisal_value * 100` quando ausente

**Decisão:** Manter o padrão de um `Normalizer` por banco. A lógica de normalização específica fica encapsulada, e o schema comum permanece intacto.

---

### Q3: Algum banco tem API pública ou feed estruturado?

Nenhum dos 6 bancos oferece API pública documentada ou feed estruturado (CSV/JSON/XLSX) de imóveis:

| Banco | Situação |
|-------|----------|
| BB | Portal Java legado (.bbaction) — sem API REST pública |
| BRB | Delega para Resale (SPA React + API privada) |
| BNB | Liferay CMS — portlets assíncronos sem API pública |
| BASA | Next.js estático — dados apenas em PDFs de editais |
| Banrisul | Sistema legado .aspx — sem API |
| Banestes | Apenas editais PDF publicados no site |

Isso contrasta com a Caixa, que disponibiliza CSV por UF em URL previsível. Para os outros bancos, scraping ou extração de PDF é obrigatório.

---

### Q4: Qual o volume e como isso afeta a arquitetura?

| Tier | Bancos | Volume | Impacto Arquitetural |
|------|--------|--------|---------------------|
| **Alto** | BB | 5k–15k imóveis | Job diário, paginação, upload GCS por lote |
| **Médio** | BNB | 800–2.5k imóveis | Job 3x/semana, paginação Liferay |
| **Baixo-Médio** | BRB, Banrisul | 200–800 imóveis | Job 2x/semana, lista única ou poucas páginas |
| **Muito Baixo** | BASA, Banestes | 10–150 imóveis | Job semanal, foco em detecção de novos editais |

---

### Q5: Estratégia para bancos que só têm editais PDF (BASA, Banestes)?

Esses bancos não têm listagem estruturada. O fluxo é:

1. Coletor monitora a página de comunicados/publicações legais
2. Detecta novos links de PDFs de editais (por título ou data)
3. Baixa o PDF para o GCS
4. Publica evento no tópico `property-editais` (já existente na Fase 2)
5. O job `process_editais` (Fase 2) extrai dados com Document AI + Gemini
6. Os dados extraídos são normalizados e salvos como `Property` com `source = "edital_pdf"`

O conector para BASA/Banestes é, portanto, um **Edital Collector** — não produz `RawProperty` diretamente, mas alimenta o pipeline de IA da Fase 2. A interface `BankConnector` precisa ser estendida ou o conector implementa `discover_sources` + `fetch_raw` retornando bytes do PDF, e o `parse` passa para o extrator de IA.

**Alternativa:** Implementar apenas `discover_sources` (lista de URLs de editais) + `fetch_raw` (download do PDF). O `parse` retorna `RawProperty` com `raw_data = {"edital_bytes": base64}` e o normalizer chama o `EditalExtractor` da Fase 2.

---

## Decisões de Arquitetura

### Decisão 1: Estrutura de Diretórios

```
app/connectors/
├── base.py              # interface BankConnector (existente)
├── caixa/               # existente
├── bb/
│   ├── __init__.py
│   ├── collector.py     # BBConnector (httpx + paginação)
│   ├── parser.py        # HTML BeautifulSoup
│   └── normalizer.py    # campos BB → schema comum
├── brb/
│   ├── collector.py     # BRBConnector (Playwright + network interception)
│   ├── parser.py        # JSON da API Resale interceptada
│   └── normalizer.py
├── bnb/
│   ├── collector.py     # BNBConnector (Playwright + portlet Liferay)
│   ├── parser.py        # HTML portlet BeautifulSoup
│   └── normalizer.py
├── basa/
│   ├── collector.py     # BASAConnector (httpx + detecção de PDFs)
│   ├── parser.py        # delega para EditalExtractor (Fase 2)
│   └── normalizer.py
├── banrisul/
│   ├── collector.py     # BanrisulConnector (httpx + BeautifulSoup .aspx)
│   ├── parser.py
│   └── normalizer.py
└── banestes/
    ├── collector.py     # BanestesConnector (httpx + detecção de PDFs)
    ├── parser.py        # delega para EditalExtractor
    └── normalizer.py

jobs/
├── collect_caixa.py     # existente
├── collect_bb.py        # novo (padrão idêntico ao collect_caixa.py)
├── collect_brb.py
├── collect_bnb.py
├── collect_basa.py
├── collect_banrisul.py
└── collect_banestes.py
```

### Decisão 2: Imagens Docker

- `Dockerfile.job` já inclui Playwright — todos os novos jobs usam a mesma imagem
- Bancos que só precisam de `httpx` (BB, Banrisul, Banestes) não executarão Playwright, mas tê-lo na imagem não é problema (é uma dependência opcional no pyproject.toml, extra `playwright`)
- **Alternativa rejeitada:** imagem separada sem Playwright para BB — overhead operacional não justifica

### Decisão 3: Scheduler por Banco

| Bank | Frequência | Custo Cloud Run/mês estimado |
|------|-----------|------------------------------|
| BB | 1x/dia | ~30 execuções |
| BRB | 3x/semana | ~13 execuções |
| BNB | 3x/semana | ~13 execuções |
| BASA | 1x/semana | ~4 execuções |
| Banrisul | 2x/semana | ~9 execuções |
| Banestes | 1x/semana | ~4 execuções |

### Decisão 4: YAGNI — Features Removidas do Escopo da Fase 3

| Feature | Razão da Remoção |
|---------|-----------------|
| API unificada multi-banco em tempo real | Não existe API pública em nenhum banco — scraping é obrigatório |
| Score de oportunidade específico por banco | Score atual da Fase 1 já é agnóstico ao banco — sem alteração |
| Relatório comparativo entre bancos no frontend | Fase 4 (inteligência de mercado) |
| Detalhamento de imóvel com fotos para BB/BRB | Complexidade adicional — scraping de página de detalhe é Fase 3.5 |
| Autenticação OAuth em portais bancários | Nenhum banco exige login para consultar imóveis à venda |

---

## Prioridade de Implementação

Com base em volume, complexidade e estratégia de coleta:

1. **BB** — maior volume, estratégia clara (`httpx`), impacto imediato na plataforma
2. **BNB** — médio volume, Playwright simples, região importante (Nordeste)
3. **BRB** — baixo volume, mas Playwright + Resale tem desafio técnico interessante (network interception)
4. **Banrisul** — precisa de descoberta da URL real antes de implementar
5. **BASA** — muito baixo volume, depende do pipeline de IA da Fase 2
6. **Banestes** — muito baixo volume, última prioridade

---

## KB Domains Identificados para a Fase de Define

| KB Domain | Relevância |
|-----------|------------|
| `python` | Conectores, parsers, normalizadores |
| `gcp` | Cloud Run Jobs, Cloud Scheduler, Pub/Sub, GCS |
| `terraform` | Novos jobs, schedulers, IAM |
| `testing` | Testes unitários para cada parser/normalizer |

---

## Confidence por Decisão

| Decisão | Evidence Level | Confidence |
|---------|---------------|------------|
| Job por banco (Opção B) | KB pattern + codebase match (Fase 1) | 0.95 |
| Normalizer por banco (padrão Caixa) | Codebase pattern | 0.95 |
| BB via httpx + BeautifulSoup | Observação direta do portal www49.bb.com.br | 0.85 |
| BRB via Playwright + Resale | Resale confirmado SPA; network interception é padrão Playwright | 0.82 |
| BNB via Playwright + Liferay | Portlet confirmado por HTML; sem SSR | 0.85 |
| BASA/Banestes via PDF + pipeline IA | Formato observado no site; sem listagem estruturada | 0.90 |
| Banrisul — URL ainda a descobrir | URL não acessível; lançamento recente (abr/2026) | 0.60 |

---

## Requisitos de Sample Data

| Banco | Sample Disponível | Como Obter |
|-------|------------------|------------|
| BB | Não (portal bloqueado sem JS) | Playwright manual para capturar 1 página de listagem |
| BRB | Não (Resale SPA) | Playwright com DevTools para capturar request da API Resale |
| BNB | Não (portlet assíncrono) | Playwright para capturar HTML do portlet renderizado |
| BASA | Não (PDFs) | Download manual de 1 edital de exemplo |
| Banrisul | Não (URL desconhecida) | Inspeção manual do portal após localizar URL |
| Banestes | Não (PDFs) | Download manual de 1 edital de exemplo |

---

## Next Step

Documento BRAINSTORM completo. Pronto para `/define BRAINSTORM_FASE3_TODOS_BANCOS.md`.

Ao implementar, iniciar por `BB` (maior volume, menor complexidade técnica).
