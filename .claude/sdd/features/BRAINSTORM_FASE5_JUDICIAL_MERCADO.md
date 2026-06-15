# BRAINSTORM: Fase 5 — Leilões Judiciais + Inteligência de Mercado

> Sessão exploratória baseada em análise competitiva profunda: identificação de novas fontes (TRT, TRF, TJs, SPU, PGFN), novos leiloeiros e funcionalidades de alto impacto que nenhum concorrente oferece.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FASE5_JUDICIAL_MERCADO |
| **Date** | 2026-06-14 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Contexto

Fases 1–4 entregues. A plataforma cobre 7 bancos públicos + 5 leiloeiros (Fidalgo, Sodré, Mega, Zuk, Frazão) + score multidimensional + mapa de risco + leitura de editais com Gemini + Radar Index por UF. O diretório `app/connectors/tjsp/` existe mas está vazio.

A análise competitiva revelou que **nenhum concorrente monitora leilões judiciais de tribunais** (TRT, TRF, TJs) de forma sistemática — este é o maior gap do mercado. Leilões judiciais têm descontos médios 40–70% superiores aos extrajudiciais (20–40%), mas são os mais difíceis de localizar.

O DataJud API (`app/risk/sources/datajud.py`) já existe e já consome a API pública do CNJ. A Fase 5 o transforma de fonte de risco em **fonte de coleta primária para hastas públicas judiciais**.

---

## Análise Competitiva — Findings

### Concorrentes Tier 1 (Agregadores)

**Monitor Leilão** (`monitorleilao.com.br`)
- Agrega bancos + leiloeiros numa busca unificada
- Interface razoável, busca por mapa disponível
- **Gaps críticos:** zero score de oportunidade, zero análise de risco, zero leitura de edital com IA, zero cobertura de tribunais

**Leilão Imóvel** (`leilaoimovel.com.br`)
- Foco nos bancos públicos, design limpo, filtros básicos
- **Gaps críticos:** não cobre leiloeiros independentes, não cobre judiciais, sem alertas por critério

**Chui Leilões** (`chuileiloes.com.br`)
- Leiloeiro que agrega eventos de outros leiloeiros (cross-listing)
- **Gaps críticos:** é o próprio leiloeiro, não análise imparcial, sem score

### Concorrentes Tier 2 (Leiloeiros com portal web)

**Lance Certo** — foco forte em judicial, interface ok, sem análise automática — **não coberto hoje**
**Superleilões** — volume alto de lotes, interface datada, sem alertas — **não coberto hoje**
**Arremate** — lotes judiciais de SP, sem radar de oportunidades — **não coberto hoje**
**Biasi Leilões** — forte em SP/Sul, foco extrajudicial, sem score — **não coberto hoje**
**Smart Leilões** — crescendo, foco em SP extrajudicial — **não coberto hoje**

### Gaps Competitivos Confirmados

| Gap | Nenhum concorrente faz | Radar Imóvel já tem base para |
|-----|------------------------|-------------------------------|
| Score automático de oportunidade | ✅ (nenhum faz) | ✅ já feito |
| Leitura de edital com IA | ✅ (nenhum faz) | ✅ já feito |
| Cobertura de tribunais (TRT/TRF/TJ) | ✅ (nenhum faz) | DataJudClient já existe |
| Detector de 2ª praça | ✅ (nenhum faz) | change_detector como base |
| Calculadora ROI | ✅ (nenhum faz) | schema já tem os campos |
| Radar Index granular (cidade/bairro) | ✅ (nenhum faz) | PostGIS já instalado |
| Comparativo preço/m² vs. mercado | ✅ (nenhum faz) | FipeZap tem API pública |

---

## Pesquisa por Fonte — Novas Fontes

### A. TRT — Tribunais Regionais do Trabalho (24 regiões)

**Característica central:** Hastas públicas em processos trabalhistas com penhora de imóveis. O trabalhador ganhou a causa e o juiz penhora o bem do empregador para pagar a dívida. O imóvel vai a leilão público com formalidade total (edital publicado, datas fixas).

**Acesso via DataJud:**
- API pública: `https://api-publica.datajud.cnj.jus.br`
- O `DataJudClient` em `app/risk/sources/datajud.py` já usa essa API
- Filtros disponíveis: `classeProcessual`, `tribunal`, `assuntosCNJ`
- Tribunal codes TRT: `TRT1` (RJ), `TRT2` (SP interior), `TRT3` (MG), até `TRT24` (MS)
- Classe para hastas: filtrar por keywords "hasta pública", "leilão", "arrematação" no assunto ou tipo de decisão

**Acesso via portais específicos:**
- Cada TRT tem portal próprio de comunicações de atos (TRT2 tem sistema DEJT)
- Portal de leiloeiros oficiais de cada TRT (lista pública obrigatória)
- Diário Eletrônico da Justiça do Trabalho (DEJT) — publicação obrigatória de editais

**Volume estimado:** TRT2 (SP) tem ~5.000 hastas/ano; todos TRTs somados ~15.000–20.000 hastas/ano com imóveis

**Estratégia:** DataJudClient expandido com filtro de tribunal + classe → leiloeiro designado → edital via pipeline existente

### B. TRF — Tribunais Regionais Federais (6 regiões)

**TRF-1:** AM, AP, AC, BA, DF, GO, MA, MG, MT, PA, PI, RO, RR, TO (14 estados)
**TRF-2:** ES, RJ
**TRF-3:** MS, SP
**TRF-4:** PR, RS, SC
**TRF-5:** AL, CE, PB, PE, RN, SE
**TRF-6:** MG (criado recentemente, herdou fatia do TRF-1)

**Característica central:** Causas federais — dívidas com Receita Federal, INSS, BACEN, contratos com a União. Volume de imóveis de alto valor (empresariais, rurais, industriais) superior ao dos TRTs.

**Acesso:** Mesma API DataJud, filtrando por tribunal `TRF1` até `TRF6`
**Portais específicos:** cada TRF tem Diário Eletrônico Federal (DEJF), publicação obrigatória

**Volume estimado:** ~8.000–12.000 hastas/ano com imóveis

### C. TJ Estaduais — TJSP, TJRJ, TJMG, TJRS (prioridade)

**TJSP:** Maior volume do Brasil (~30% de todas as hastas). Diretório `app/connectors/tjsp/` JÁ EXISTE mas vazio.
- Portal público de hastas: e-leilões.com.br (plataforma usada pelo TJSP para leilões eletrônicos)
- DataJud já retorna processos do TJSP — filtro por classe processual
- Leiloeiros credenciados: Fidalgo, Sodré, Mega, Zuk — JÁ COBERTOS

**TJRJ:** Segundo maior volume. Portal próprio e leiloeiros credenciados listados.
**TJMG:** Terceiro maior. Sistema SISCOM para publicação de atos.
**TJRS:** Volume alto no Sul. Portal e-leilões (mesmo da TJSP para alguns casos).

**Estratégia:** DataJud como fonte de descoberta → leiloeiro designado como fonte de detalhes

### D. SPU — Secretaria do Patrimônio da União

**O que é:** Órgão federal que administra bens imóveis da União. Aliena bens por concorrência pública, licitação e leilão. Inclui terrenos de marinha, imóveis funcionais, antigas instalações militares.

**Acesso:** Portal gov.br/spu tem seção "Alienação de Imóveis" com lista pública. API de dados abertos do governo federal pode ter dados estruturados.

**Volume:** ~500–1.500 bens/ano, mas de alto valor unitário (terrenos enormes, imóveis históricos)

**Estratégia:** Scraping do portal gov.br/spu + Diário Oficial (DOU seção 3)

### E. PGFN — Procuradoria-Geral da Fazenda Nacional

**O que é:** Leiloar bens penhorados de devedores fiscais (CNPJ com dívida tributária ativa). Imóveis vão a leilão para quitação parcial da dívida.

**Acesso:** Portal PGFN tem seção de leilões públicos. O Diário Oficial (DOU) publica todos os editais.

**Volume:** Médio, mas imóveis de valor alto (sedes de empresas, galpões, propriedades rurais)

### F. Receita Federal — Bens Apreendidos

**O que é:** Imóveis apreendidos ou confiscados em operações fiscais/criminais. Vendidos via licitação pública.

**Acesso:** Portal de licitações da Receita Federal + DOU seção 3
**Volume:** Baixo, mas casos específicos de alto desconto

### G. Novos Leiloeiros não cobertos

| Leiloeiro | Especialidade | Volume | Prioridade |
|-----------|--------------|--------|-----------|
| **Lance Certo** | Judicial (TRT/TRF/TJ) | Alto | P0 |
| **Superleilões** | Misto (judicial + extrajudicial) | Alto | P0 |
| **Arremate** | Judicial SP/RJ | Alto | P1 |
| **Biasi Leilões** | Sul (PR/SC/RS) + judicial | Médio | P1 |
| **Smart Leilões** | SP extrajudicial | Médio | P2 |
| **BLL (Bolsa de Licitações)** | Governo (federal/estadual) | Alto | P2 |
| **Portal e-Leilões** | TJSP eletrônico | Alto | P1 |

---

## Pesquisa por Funcionalidade

### F1: Detector de 2ª Praça (Quick Win — maior impacto por esforço)

**O problema:** Quando um imóvel não é arrematado na 1ª praça, vai automaticamente à 2ª praça com valor mínimo reduzido (geralmente 50% do valor de avaliação). Esta é a **maior oportunidade** — é quando os maiores descontos aparecem. Nenhum concorrente detecta isso automaticamente.

**Base técnica existente:**
- `change_detector` já detecta mudanças por `(external_code, bank_id)`
- O campo `minimum_value` já existe na tabela `properties`
- O score já é recalculado a cada mudança

**Implementação:** comparar `minimum_value` atual vs. anterior. Se cair ~50% e o `external_code` for o mesmo imóvel, é 2ª praça. Gerar alerta prioridade máxima (P0) para usuários com watchlist.

**Dados históricos necessários:** `property_changes` (já existe com `old_value`/`new_value`)

### F2: Calculadora ROI

**O problema:** O usuário sabe o preço do lance mas não sabe se vale a pena financeiramente versus outras aplicações.

**Inputs:**
- Preço do lance (do imóvel)
- Intenção: revenda / aluguel / moradia
- Custo estimado de reforma (R$/m² configurável)
- Horizonte de investimento (meses)

**Outputs:**
- ROI de revenda: `(preço_mercado - lance - reforma) / (lance + reforma)`
- Yield de aluguel: `aluguel_mensal_estimado * 12 / (lance + reforma)`
- Payback em meses
- Comparativo com CDB 100% CDI no mesmo período (taxa Selic)
- Break-even point

**Fonte do preço de mercado:** FipeZap (API pública de índice por cidade) + scraping de anúncios similares

### F3: Integração FipeZap — Preço/m² por Cidade

**O que é:** FipeZap publica mensalmente o índice de preço médio por m² de imóveis residenciais nas principais cidades brasileiras. Existe endpoint de dados abertos.

**Implementação:** Job mensal que baixa dados FipeZap e popula tabela `market_prices(city, uf, property_type, price_per_sqm_sale, price_per_sqm_rent, reference_month)`.

**Uso:** Card do imóvel exibe "R$ X/m² vs. R$ Y/m² de mercado em [cidade] = Z% abaixo"

### F4: Radar Index Granular (Município → Bairro)

**Estado atual:** Radar Index agrega por UF.
**Melhoria:** PostGIS já instalado + `latitude`/`longitude` já nos imóveis → agregar por município e depois por bairro (via reverse geocoding que já existe no pipeline de geodados).

**Novas dimensões:**
- Tendência: deságio subindo ou descendo nos últimos 3/6 meses no município?
- "Hotspots" de oportunidade: bairros com maior concentração de imóveis acima de 30% de desconto
- Mapa de calor de oportunidade (deságio), distinto do mapa de risco existente

### F5: Due Diligence PDF Expandido

**Estado atual:** `app/risk/pdf_report.py` existe com relatório básico.
**Melhoria:** Relatório completo com:
- Score de oportunidade e detalhe por dimensão
- Análise de risco multidimensional com fonte de cada dado
- Resumo do edital extraído pela IA (Gemini)
- Preço/m² vs. mercado local
- Processos judiciais vinculados (DataJud)
- Links para certidões públicas relevantes
- Seção de alertas e riscos identificados
- Formato white-label (logo do usuário ou da corretora)

### F6: Watchdog de Processos Judiciais em Favoritos

**Lógica:** Imóvel favoritado → o sistema monitorar processos DataJud vinculados → alertar se:
- Nova penhora registrada sobre o imóvel
- Recurso que pode suspender hasta pública
- Decisão de adjudicação (arrematado por credor)
- Data da hasta remarcada

**Fonte:** DataJud API já implementado + webhook polling (job diário por imóvel favoritado com processo vinculado)

---

## Arquitetura de Coleta — Fonte Judicial Unificada

```
DataJud API (CNJ) ──▶ JudicialConnector ──▶ Pipeline existente
                           │
                    filtra por tribunal:
                    - TRT-1 a TRT-24
                    - TRF-1 a TRF-6
                    - TJSP, TJRJ, TJMG, TJRS...
                           │
                    classifica por classe processual:
                    - Hasta Pública
                    - Penhora Ativa
                    - Arrematação
                           │
                    resolve leiloeiro designado ──▶ connector existente
                    (Fidalgo, Sodré, Lance Certo, etc.)
```

**Vantagem arquitetural:** O `DataJudClient` existente em `app/risk/sources/datajud.py` já tem todos os métodos necessários — só precisa ser reposicionado como **fonte primária de coleta** (não apenas fonte de risco) e ter filtros de tribunal adicionados.

---

## Prioridade Final por Impacto/Esforço

| Feature | Impacto | Esforço | Base existente | P |
|---------|---------|---------|----------------|---|
| Detector 2ª Praça | Muito alto | Muito baixo | change_detector | **P0** |
| TJSP connector (diretório existe) | Alto | Baixo | tjsp/ + DataJudClient | **P0** |
| TRT via DataJud expandido | Alto | Baixo | DataJudClient | **P0** |
| Lance Certo connector | Alto | Médio | base BankConnector | **P1** |
| Superleilões connector | Alto | Médio | base BankConnector | **P1** |
| FipeZap preço/m² | Alto | Médio | models existentes | **P1** |
| Calculadora ROI | Alto | Médio | schema completo | **P1** |
| TRF via DataJud expandido | Alto | Baixo | DataJudClient | **P1** |
| Arremate + Biasi connectors | Médio | Médio | base BankConnector | **P2** |
| Portal e-Leilões (TJSP eletrônico) | Alto | Alto | — | **P2** |
| SPU bens da União | Médio | Baixo | httpx + scraping | **P2** |
| Radar Index por município | Alto | Baixo | PostGIS + geo | **P2** |
| Due Diligence PDF expandido | Médio | Médio | pdf_report.py | **P2** |
| Watchdog processos judiciais | Alto | Alto | DataJudClient | **P3** |
| PGFN/Receita Federal | Médio | Alto | — | **P3** |
| PWA + Push Notifications | Alto | Alto | Next.js | **P3** |

---

## Questões em Aberto

| ID | Questão | Impacto na decisão |
|----|---------|-------------------|
| OQ-01 | DataJud tem rate limit configurado? Quantas requests/min são seguras para coleta contínua? | Dimensiona pool de jobs e frequência do scheduler |
| OQ-02 | Lance Certo e Superleilões têm API pública ou apenas HTML? | Define se precisamos Playwright ou httpx basta |
| OQ-03 | Portal e-leilões (TJSP eletrônico) exige cadastro/login? | Pode bloquear coleta automatizada |
| OQ-04 | FipeZap tem endpoint de dados abertos JSON ou apenas PDF/Excel? | Define complexidade do parser |
| OQ-05 | Como identificar que dois registros (leiloeiro A + DataJud) são o mesmo imóvel físico? | Chave de deduplicação inter-fonte |
| OQ-06 | Watchdog de processos judiciais: polling diário ou Pub/Sub push do DataJud? | Arquitetura de atualização |

---

## Próximo Passo

Continuar para `DEFINE_FASE5_JUDICIAL_MERCADO.md` com os requisitos priorizados das features P0 e P1.
