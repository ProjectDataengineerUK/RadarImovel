# DEFINE: Mapa de Risco de Imóveis

> Score de risco multidimensional por imóvel + mapa de calor visual no dashboard, usando bases públicas IBGE, TCE/IPTU, CNJ/TJ e INCRA/Cartório. Diferencial competitivo: cruzamento auditável de 10+ fontes públicas que nenhum portal imobiliário replicou.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | MAPA_RISCO_IMOVEIS |
| **Date** | 2026-06-08 |
| **Author** | define-agent |
| **BRAINSTORM** | — (input direto) |
| **Status** | ✅ Shipped |
| **Clarity Score** | 15/15 |

---

## 1. Problema

Compradores de imóveis em leilão tomam decisões com informação incompleta. O preço de desconto aparente pode ocultar riscos cumulativos — dívida de IPTU de 10 anos + processo judicial de inventário + imóvel em APP — que tornam a arrematação economicamente inviável. Não existe hoje nenhuma plataforma brasileira que cruze automaticamente dados públicos de múltiplas fontes (judicial, fundiário, fiscal, ambiental, socioeconômico) para gerar um risco consolidado por imóvel e por região.

**Impacto sem a feature:** usuários arremateiam imóveis sem saber que há uma penhora judicial adicional, que o imóvel está em área de inundação CEMADEN, ou que o município tem dívida ativa superior ao valor do bem.

---

## 2. Usuários e Personas

| Persona | Descrição | Dor principal |
|---------|-----------|---------------|
| **Investidor pessoa física** | Compra 1-3 imóveis/ano em leilão como renda extra | Não sabe avaliar risco jurídico sem advogado |
| **Investidor profissional** | Compra 10+ imóveis/ano, precisa de escala | Due diligence manual custa R$ 500-2.000 por imóvel |
| **Advogado/consultor** | Assessora clientes em arrematações | Precisa de dados consolidados para laudos rápidos |
| **Administrador de carteira** | Fundo imobiliário com imóveis adquiridos em leilão | Precisa de risco quantitativo para pricing e provisionamento |

---

## 3. Objetivos e Metas

| # | Objetivo | Métrica de sucesso |
|---|----------|--------------------|
| O-1 | Calcular score de risco para 100% dos imóveis coletados | ≥95% com score calculado em até 24h da coleta |
| O-2 | Exibir mapa de calor de risco por região | Mapa disponível no dashboard com granularidade municipal + bairro (quando disponível) |
| O-3 | Alertar quando risco de imóvel favorito muda | Notificação Telegram/email em até 1h da detecção da mudança |
| O-4 | Score auditável por dimensão | Cada componente do score exibe fonte, data e valor bruto |
| O-5 | Relatório de due diligence exportável | PDF gerado em até 30s com todas as dimensões e fontes |

---

## 4. Dimensões de Risco — Taxonomia Completa

### Dimensão A — Risco Jurídico (peso padrão: 30%)

| Código | Indicador | Fonte | Cálculo |
|--------|-----------|-------|---------|
| A-1 | Processos ativos vinculados ao imóvel (matrícula/endereço) | CNJ Datajud API | +10 pts/processo ativo |
| A-2 | Processo de inventário/partilha em andamento | CNJ Datajud | +15 pts se inventário não concluído |
| A-3 | Disputa de posse ou usucapião | CNJ Datajud | +20 pts |
| A-4 | Cônjuge meeiro identificado sem anuência no edital | Edital (Gemini, Fase 2) | +25 pts |
| A-5 | Ação anulatória de arrematação anterior | CNJ Datajud | +30 pts |
| A-6 | Arresto ou penhora adicional sobre o bem | CNJ Datajud | +15 pts/penhora |
| A-7 | Alienação fiduciária não extinta (outra instituição) | Cartório/SINTER | +20 pts |
| A-8 | Imóvel em massa falida ou recuperação judicial | CNJ Datajud | +25 pts |
| A-9 | Ação de despejo ativa com ocupante resistente | CNJ Datajud | +10 pts |

### Dimensão B — Risco Fundiário e Ambiental (peso padrão: 20%)

| Código | Indicador | Fonte | Cálculo |
|--------|-----------|-------|---------|
| B-1 | Matrícula irregular ou inexistente | Cartório/SINTER/INCRA | +30 pts |
| B-2 | Sobreposição com APP (Área de Preservação Permanente) | IBAMA/MapBiomas API | +25 pts |
| B-3 | Sobreposição com APA ou Unidade de Conservação | IBAMA MMA | +15 pts |
| B-4 | Sobreposição com terra indígena ou quilombola | FUNAI/INCRA | +40 pts |
| B-5 | Imóvel em zona de alto/muito alto risco CEMADEN (deslizamento) | CEMADEN API | +20/+35 pts |
| B-6 | Imóvel em zona de inundação (enchente recorrente) | CEMADEN / Defesa Civil | +15/+25 pts |
| B-7 | Faixa de domínio (ferrovia, rodovias federais, LT energia) | DNIT/ANEEL shapefiles | +20 pts |
| B-8 | REURB-S pendente (regularização fundiária de interesse social) | SINTER/município | +10 pts |
| B-9 | Área rural sem CAR (Cadastro Ambiental Rural) | SICAR/IBAMA | +10 pts |
| B-10 | Área contaminada ou suspeita de contaminação | CETESB/IBAMA lista pública | +30 pts |

### Dimensão C — Risco Fiscal (peso padrão: 20%)

| Código | Indicador | Fonte | Cálculo |
|--------|-----------|-------|---------|
| C-1 | Dívida ativa IPTU acumulada | Portal transparência municipal / TCE | R$ dívida ÷ valor venal × 100 (caps a 30 pts) |
| C-2 | Número de exercícios de IPTU em atraso | Portal transparência | +3 pts/ano em atraso (max 20 pts) |
| C-3 | Dívida ativa municipal (outras taxas: TLP, TLF, etc.) | Portal transparência | +10 pts se > R$ 5k |
| C-4 | Dívida ativa estadual (ITCMD, IPVA imóvel rural) | SEFAZ estadual | +10 pts se > R$ 5k |
| C-5 | Auto de infração ambiental ativo | IBAMA/ICMBio | +15 pts |
| C-6 | Embargo de obra pela prefeitura | Portal transparência / CREA | +20 pts |

### Dimensão D — Risco de Ocupação (peso padrão: 15%)

| Código | Indicador | Fonte | Cálculo |
|--------|-----------|-------|---------|
| D-1 | Imóvel declarado ocupado no edital | Edital (Gemini, Fase 2) | +20 pts base |
| D-2 | Tipo de ocupação: invasão irregular vs inquilino | Edital | +10 pts extra para invasão |
| D-3 | Múltiplos ocupantes declarados | Edital | +5 pts/ocupante adicional |
| D-4 | CNPJ ativo com endereço no imóvel | Receita Federal CNPJ API | +15 pts (complexidade de desocupação) |
| D-5 | Menores de idade declarados no imóvel | Edital | +15 pts (proteção ECA) |
| D-6 | Processo de reintegração de posse já em curso | CNJ Datajud | -10 pts (risco parcialmente mitigado) |

### Dimensão E — Risco Socioeconômico (peso padrão: 10%)

| Código | Indicador | Fonte | Cálculo |
|--------|-----------|-------|---------|
| E-1 | IDH municipal < 0,650 (baixo) | IBGE SIDRA / PNUD | +15 pts |
| E-2 | IDH municipal 0,650–0,749 (médio) | IBGE SIDRA / PNUD | +8 pts |
| E-3 | Taxa de homicídios > 30/100k hab (município) | Atlas da Violência IPEA / SINESP | +15 pts |
| E-4 | Taxa de homicídios 15–30/100k (município) | Atlas da Violência IPEA | +8 pts |
| E-5 | Decrescimento populacional > 5% (última década) | IBGE Censo 2022 | +10 pts |
| E-6 | Renda domiciliar média < R$ 1.500/mês (setor censitário) | IBGE Censo 2022 | +8 pts |
| E-7 | Taxa de vacância imobiliária > 20% no município | IBGE Censo 2022 | +10 pts |
| E-8 | Setor censitário classificado como aglomerado subnormal | IBGE | +12 pts |

### Dimensão F — Risco de Mercado e Liquidez (peso padrão: 5%)

| Código | Indicador | Fonte | Cálculo |
|--------|-----------|-------|---------|
| F-1 | Preço/m² do imóvel acima da mediana local (desconto nominal vs real) | Fipe ZAP API / OLX Imóveis | +15 pts se acima da mediana |
| F-2 | Tempo médio de venda > 12 meses na cidade/tipo | Fipe ZAP / Imovelweb trends | +10 pts |
| F-3 | Estoque de similares > 2× média histórica (oversupply) | Fipe ZAP / ADEMI | +5 pts |
| F-4 | Município sem crescimento de transações imobiliárias (3 anos) | ITBI municipal (portal transp.) | +8 pts |

---

## 5. Score Consolidado

### Fórmula de cálculo

```
score_risco = (
    sum(A) × 0.30 +
    sum(B) × 0.20 +
    sum(C) × 0.20 +
    sum(D) × 0.15 +
    sum(E) × 0.10 +
    sum(F) × 0.05
) normalizado para 0–100
```

Pesos configuráveis via `settings.py` (análogo ao score de oportunidade existente).

### Faixas de risco

| Score | Classificação | Cor | Ação recomendada |
|-------|--------------|-----|------------------|
| 0–20 | Risco Baixo | Verde `#22c55e` | Oportunidade — due diligence simplificada |
| 21–40 | Risco Moderado | Amarelo `#eab308` | Verificar dimensões acima de 0 antes de arrematar |
| 41–60 | Risco Elevado | Laranja `#f97316` | Consultar advogado; calcular custo de regularização |
| 61–80 | Risco Alto | Vermelho `#ef4444` | Arrematar apenas com grande margem ou especialização |
| 81–100 | Risco Crítico | Preto `#18181b` | Evitar ou hedge legal completo |

---

## 6. Mapa de Calor

### Granularidade

| Nível | Fonte geoespacial | Quando disponível |
|-------|-----------------|-------------------|
| Município | IBGE malha municipal (GeoJSON) | Sempre |
| Bairro/Setor censitário | IBGE Censo 2022 setores | Quando CEP geolocalizado |
| Imóvel pontual | Lat/lng do próprio imóvel | Sempre (geocoding Fase 1) |

### Camadas do mapa

| Camada | Dado | Toggle no dashboard |
|--------|------|---------------------|
| Heat map de risco médio por município | Média do `score_risco` dos imóveis coletados | Padrão: ON |
| Pontos de imóveis disponíveis | Imóvel individual colorido pelo score | Padrão: ON |
| Overlay ambiental | APP/APA/UC (GeoJSON IBAMA) | OFF (opt-in) |
| Overlay de risco CEMADEN | Zonas de deslizamento/inundação | OFF (opt-in) |
| Overlay de IDH municipal | Gradiente por IDH IBGE | OFF (opt-in) |
| Overlay de homicídios | Gradiente por taxa SINESP/IPEA | OFF (opt-in) |

### Tecnologia

- **Biblioteca:** Leaflet.js + `leaflet.heat` (heatmap plugin)
- **Tiles:** OpenStreetMap (gratuito) — ou Mapbox GL JS (opt-in para usuários premium)
- **GeoJSON:** servido pela API FastAPI via endpoint `/api/v1/map/risk-heatmap?uf=SP`
- **Cache:** Cloud Storage para GeoJSONs estáticos (IBGE, IBAMA, CEMADEN) com TTL 30 dias

---

## 7. Pipeline de Dados de Risco

### Fontes e estratégia de ingestão

| Fonte | Tipo | Frequência | Estratégia |
|-------|------|-----------|------------|
| **CNJ Datajud** | API REST pública | Por imóvel (on-demand + batch semanal) | Busca por endereço + matrícula; enfileira via `risk-events` Pub/Sub |
| **IBGE SIDRA** | API REST pública | Mensal (dados mudam pouco) | Download bulk por município; cache Cloud Storage |
| **IBGE Censo 2022 — Setores** | GeoJSON + CSV bulk | Anual | Download bulk; indexado por setor censitário no PostgreSQL/PostGIS |
| **CEMADEN** | API REST + shapefiles | Semanal | GeoJSON de zonas de risco; PostGIS spatial join |
| **IBAMA** | Shapefiles WFS | Mensal | APP/APA/UC GeoJSON; PostGIS spatial join |
| **INCRA/SIGEF** | Shapefiles | Mensal | Imóveis rurais; spatial join |
| **Portais Transparência** | HTML/CSV por município | Semanal | Scraping por CEP/inscrição imobiliária |
| **Atlas da Violência (IPEA)** | CSV/API | Anual | Download por ano; enriquece por município |
| **Receita Federal CNPJ** | API pública | Por imóvel (on-demand) | Consulta CNPJ por endereço |
| **Fipe ZAP / OLX Imóveis** | API parceira / scraping | Diário | Preço/m² por cidade/bairro |

### Novo Job: `jobs/calculate_risk.py`

```text
Trigger: Pub/Sub `risk-events` (publicado por collect_bank ao criar/atualizar Property)
Ação:
  1. Para cada Property nova/modificada:
     a. Consultar CNJ Datajud (A-1 a A-9)
     b. Spatial join PostGIS: CEMADEN, IBAMA, IBGE setores (B, E)
     c. Buscar dívida IPTU por CEP/inscrição (C-1 a C-6)
     d. Ler dados de ocupação do edital já processado (D, Fase 2)
     e. Calcular score por dimensão e score consolidado
     f. Salvar em `property_risk_scores` (tabela nova)
     g. Se score mudou > 10 pts → publicar `risk-change-events`
```

---

## 8. Schema de Dados

### Tabela `property_risk_scores`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUID | PK |
| `property_id` | UUID FK | Referência a `properties` |
| `score_total` | FLOAT | 0–100 |
| `score_juridico` | FLOAT | Dimensão A |
| `score_fundiario` | FLOAT | Dimensão B |
| `score_fiscal` | FLOAT | Dimensão C |
| `score_ocupacao` | FLOAT | Dimensão D |
| `score_socioeconomico` | FLOAT | Dimensão E |
| `score_mercado` | FLOAT | Dimensão F |
| `risk_level` | VARCHAR(10) | `low/moderate/elevated/high/critical` |
| `indicators` | JSONB | `{A1: {value: 2, source: "CNJ", date: "..."}, ...}` |
| `calculated_at` | TIMESTAMPTZ | Quando o score foi calculado |
| `sources_consulted` | TEXT[] | Lista de fontes acessadas |
| `calculation_version` | VARCHAR(10) | Versão do algoritmo (para comparação) |

### Tabela `risk_geodata_cache`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUID | PK |
| `layer_type` | VARCHAR(30) | `cemaden_deslizamento`, `ibama_app`, `ibge_setor`, etc. |
| `municipality_code` | VARCHAR(7) | Código IBGE 7 dígitos |
| `geojson_url` | TEXT | GCS path |
| `cached_at` | TIMESTAMPTZ | |
| `expires_at` | TIMESTAMPTZ | |

---

## 9. API Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/v1/properties/{id}/risk` | Score completo do imóvel + indicadores auditáveis |
| `GET` | `/api/v1/map/risk-heatmap` | GeoJSON com risco médio por município/bairro |
| `GET` | `/api/v1/map/layers/{layer_type}` | GeoJSON de camada ambiental (APP, CEMADEN, etc.) |
| `POST` | `/api/v1/admin/recalculate-risk/{property_id}` | Forçar recálculo |
| `GET` | `/api/v1/properties/{id}/risk/report` | Gerar PDF de due diligence |

---

## 10. Frontend — Componentes

| Componente | Localização | Descrição |
|------------|-------------|-----------|
| `RiskScoreBadge` | `components/RiskScoreBadge.tsx` | Badge com cor + score + label (substitui/complementa `ScoreBadge`) |
| `RiskRadarChart` | `components/RiskRadarChart.tsx` | Radar chart com 6 dimensões (Recharts) |
| `RiskIndicatorList` | `components/RiskIndicatorList.tsx` | Lista auditável: indicador + fonte + valor + data |
| `RiskMap` | `components/RiskMap.tsx` | Leaflet + heat layer + pontos + toggle de camadas |
| `DueDiligenceReport` | `components/DueDiligenceReport.tsx` | Preview do PDF exportável |
| `app/mapa/page.tsx` | `app/mapa/page.tsx` | Página full-screen do mapa de calor |
| `app/imoveis/[id]/page.tsx` | (modificação) | Adicionar seção de risco abaixo do edital |

---

## 11. Alertas de Mudança de Risco

Extensão do `alert_agent` existente:

- **Trigger:** `risk-change-events` Pub/Sub (publicado por `calculate_risk` quando score muda > 10 pts)
- **Condição:** usuário tem o imóvel em favoritos ou watchlist com `notify_risk_changes=true`
- **Mensagem Telegram:** "⚠️ Risco do imóvel XYZ aumentou de MODERADO para ALTO — novo processo judicial detectado (CNJ, 2026-06-08). Ver detalhes: [link]"

---

## 12. Critérios de Aceite

| ID | Dado | Cenário | Resultado esperado |
|----|------|---------|-------------------|
| AT-001 | Imóvel com matrícula em APP (IBAMA) + dívida IPTU 5 anos + processo judicial ativo | `calculate_risk` executa | Score total ≥ 60 (risco alto); `indicators.B2.value=true`, `indicators.C2.value=5`, `indicators.A1.value=1`; `risk_level="high"` |
| AT-002 | Imóvel rural sem sobreposições, sem dívidas, sem processos, município IDH > 0.75 | `calculate_risk` executa | Score total ≤ 20; `risk_level="low"` |
| AT-003 | Imóvel já calculado é re-executado sem mudanças | `calculate_risk` executa novamente | Score idêntico; nenhum evento `risk-change-events` publicado |
| AT-004 | Novo processo judicial detectado no CNJ para imóvel com score 30 | CNJ retorna 1 processo novo | Score atualizado para ≥ 40; `risk-change-events` publicado; alert Telegram enviado ao usuário que favoritou |
| AT-005 | Usuário acessa `/mapa` | Dashboard carrega | Mapa exibe heat map por município; toggle de camadas funciona; ao clicar em município, lista imóveis disponíveis com score |
| AT-006 | Usuário clica "Exportar due diligence" em imóvel com score calculado | Frontend solicita `/risk/report` | PDF gerado em ≤ 30s; contém todas as 6 dimensões, indicadores, fontes e datas |
| AT-007 | Indicador B-4 (terra indígena) | Imóvel com lat/lng dentro de TI homologada | Score B-4 = +40 pts; `risk_level` mínimo = "high" independente de outros |
| AT-008 | API CNJ indisponível | `calculate_risk` executa com CNJ offline | Score calculado com `A = null`; `sources_consulted` registra `"cnj: unavailable"`; imóvel marcado como `score_partial=true` |

---

## 13. Fora do Escopo (esta fase)

| Item | Motivo |
|------|--------|
| Consulta de matrículas no Cartório (SINTER) | API SINTER ainda não é pública; depende de integração paga por ofício |
| Dados de condomínio inadimplente | Não há base pública; mencionado apenas no edital (coberto pela Fase 2) |
| Score de risco para imóveis rurais (INCRA SIGEF) | Alta complexidade fundiária rural; fase futura dedicada |
| Dados de qualidade do solo (CETESB/INEA) | Bases estaduais fragmentadas; cobertura parcial |
| Scraping de portais de preço (Fipe ZAP) | Requer API paga ou scraping frágil; Dimensão F opcional/configurável |
| Integração com certidões de cartório pagas | Modelo de negócio B2B; fora do MVP |

---

## 14. Dependências

| Dependência | Tipo | Responsável | Status |
|-------------|------|-------------|--------|
| Fase 2 (editais Gemini) | Dados de ocupação (Dim. D) | Concluído | ✅ |
| Geocoding (Fase 1) | Lat/lng para spatial joins | Concluído | ✅ |
| PostGIS habilitado | Spatial joins (B, E camadas) | Terraform já inclui PostGIS | ✅ |
| CNJ Datajud API key | Consultas judiciais | A solicitar | ❌ Pendente |
| CEMADEN shapefiles | Zonas de risco | Download público | ✅ |
| IBAMA WFS (APP/APA) | Camadas ambientais | Download público | ✅ |
| IBGE Censo 2022 setores | Dados socioeconômicos | Download público | ✅ |
| Leaflet.js no frontend | Mapa interativo | `npm install leaflet leaflet.heat` | Pendente build |
| Recharts no frontend | Radar chart | `npm install recharts` | Pendente build |

---

## 15. Não-Funcionais

| Requisito | Valor |
|-----------|-------|
| Latência do score (cálculo completo) | ≤ 5 minutos após coleta do imóvel |
| Latência da API `/properties/{id}/risk` | ≤ 500ms (score já calculado) |
| Disponibilidade dos GeoJSONs de mapa | ≥ 99.5% (servidos do GCS, não de APIs externas) |
| Score parcial (quando API externa indisponível) | Calculado com dimensões disponíveis; `score_partial=true` |
| Auditabilidade | 100% dos indicadores têm `source`, `value` e `date` no JSONB |
| Versão do algoritmo | `calculation_version` permite comparar scores históricos após mudança de pesos |

---

## 16. Dependências Técnicas Novas

| Pacote | Extra | Uso |
|--------|-------|-----|
| `httpx[http2]` | `job` | Consultas CNJ/IBGE (já presente) |
| `geopandas>=0.14` | `job` (novo) | Spatial joins para CEMADEN/IBAMA/IBGE setores |
| `shapely>=2.0` | `job` (novo, dep. geopandas) | Operações geométricas |
| `reportlab>=4.0` ou `weasyprint>=62` | `job` (novo) | Geração de PDF de due diligence |
| `leaflet` + `leaflet.heat` | `frontend` npm | Mapa interativo + heat layer |
| `recharts` | `frontend` npm | Radar chart das 6 dimensões |

---

**Clarity Score:** 15/15  
**Ready for:** `/design .claude/sdd/features/DEFINE_MAPA_RISCO_IMOVEIS.md`
