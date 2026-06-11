# DEFINE: Ingestão de Geodados de Risco

> Job de carga inicial (e atualização periódica) das bases geoespaciais e socioeconômicas que alimentam as Dimensões B (Fundiário/Ambiental) e E (Socioeconômico) do Mapa de Risco de Imóveis. Sem esses dados carregados no banco, essas dimensões retornam `partial=True` e o score é incompleto para 100% dos imóveis.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | INGESTAO_GEODADOS_RISCO |
| **Date** | 2026-06-11 |
| **Author** | define-agent |
| **BRAINSTORM** | — (input direto) |
| **Status** | ✅ Shipped |
| **Clarity Score** | 15/15 |

---

## 1. Problema

As tabelas `risk_geodata_layers` e `ibge_municipality_stats` foram criadas pela migration 006, mas estão **vazias**. Enquanto isso:

- `IbamaLookup.contains_point()` sempre retorna `[]` → Dimensão B = 0 pts, `partial=True`
- `CemadenLookup.risk_zones()` sempre retorna `[]` → Dimensão B = 0 pts, `partial=True`
- `IbgeLookup.get_stats()` sempre retorna `None` → Dimensão E = 0 pts, `partial=True`
- `IpeaAtlas.get_homicide_rate()` retorna `None` para todo município → homicídio ignora

**Consequência real:** 100% dos imóveis calculados agora têm `score_partial=True` e Dimensões B e E zeradas — o score de risco é sistematicamente subestimado. Um imóvel em APP ou em município com alto índice de homicídios recebe o mesmo score que um imóvel em zona rural segura.

**Impacto sem a feature:** o diferencial competitivo do Radar Imóvel (cruzamento auditável de bases públicas) não existe de fato — só a arquitetura existe.

---

## 2. Usuários e Personas

| Persona | Dor principal |
|---------|---------------|
| **Operador/DevOps** | Precisa rodar a carga inicial e configurar atualização periódica sem intervenção manual |
| **Sistema (calculate_risk)** | Precisa encontrar dados nas tabelas para calcular Dimensões B e E |
| **Investidor (usuário final)** | Precisa que o score de risco reflita riscos ambientais e socioeconômicos reais |

---

## 3. Objetivos e Metas

| # | Objetivo | Métrica de sucesso |
|---|----------|--------------------|
| O-1 | Carregar shapefiles IBAMA (APP, APA, UC, TI) no PostGIS | `risk_geodata_layers` com ≥1 polígono por layer_type; consulta por lat/lng de SP retorna resultado em <100ms |
| O-2 | Carregar zonas de risco CEMADEN (deslizamento, inundação) | `risk_geodata_layers` com layer_type IN ('deslizamento', 'inundacao'); ≥100 municípios cobertos |
| O-3 | Popular `ibge_municipality_stats` com todos os municípios brasileiros | 5.570 municípios com ibge_code, name, state, population_2022; ≥90% com idh preenchido |
| O-4 | Criar `data/atlas_violencia.csv` com taxas de homicídio por município | Arquivo presente no container; ≥4.000 municípios com homicide_rate não-nulo |
| O-5 | Job idempotente e re-executável | Rodar 2× não duplica dados; re-execução sobreescreve dados existentes |
| O-6 | Carga completa em <30 min no Cloud Run | Job conclui dentro do timeout de 1h com log de progresso |

---

## 4. Fontes de Dados e URLs

### 4.1 IBAMA — Áreas Protegidas (Dimensão B)

| Layer | Fonte | URL / Endpoint | Formato |
|-------|-------|----------------|---------|
| UC (Unidades de Conservação federais) | ICMBio WFS público | `https://geo.icmbio.gov.br/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=CADASTRO_UC_WGS84&outputFormat=application/json` | GeoJSON |
| TI (Terras Indígenas) | FUNAI shapefile | `https://geoserver.funai.gov.br/geoserver/Funai/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=Funai:tis_poligonais_portarias&outputFormat=application/json` | GeoJSON |
| APP (Área de Preservação Permanente) | SNIRH/ANA GeoServer | Não há WFS nacional unificado; usar polígonos de faixas de APP via buffer sobre hidrografia IBGE | Derivado |
| APA (Áreas de Proteção Ambiental) | ICMBio WFS (subset de UC) | Filtrar `cat_uc = 'APA'` no WFS de UC | GeoJSON (filter) |

> **Decisão de escopo:** Para MVP, carregar UC (inclui APA como subconjunto) e TI do WFS público. APP derivada de buffer não está no escopo desta fase — indicador B-2 fica com `partial=True` até fase específica.

### 4.2 CEMADEN — Zonas de Risco (Dimensão B)

| Layer | Fonte | URL | Formato |
|-------|-------|-----|---------|
| Municípios em risco de deslizamento | CEMADEN portal | `http://www.cemaden.gov.br/wp-content/uploads/2022/04/municipios_monitorados_deslizamento.geojson` ou CSV com ibge_code | CSV/GeoJSON |
| Municípios em risco de inundação | CEMADEN portal | `http://www.cemaden.gov.br/wp-content/uploads/2022/04/municipios_monitorados_inundacao.geojson` | CSV/GeoJSON |

> **Nota:** CEMADEN disponibiliza lista de municípios monitorados; os polígonos de risco por setor são mais granulares mas requerem download por município. Para MVP: usar polígono do município inteiro (malha IBGE) para os municípios monitorados — mesma resolução que o cálculo atual usa.

### 4.3 IBGE — Estatísticas Municipais (Dimensão E)

| Dado | Fonte | URL | Formato |
|------|-------|-----|---------|
| Malha municipal (polígonos) | IBGE | `https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2022/Brasil/BR/BR_Municipios_2022.zip` | Shapefile |
| População 2022 | IBGE Censo 2022 | SIDRA tabela 4709 via API: `https://servicodados.ibge.gov.br/api/v3/agregados/4709/periodos/2022/variaveis/93?localidades=N6` | JSON |
| IDH Municipal | Atlas Brasil / PNUD | CSV download: `http://www.atlasbrasil.org.br/ranking` → arquivo `atlas2013_dadosbrutos_pt.xlsx` | XLSX |
| Renda domiciliar média | IBGE Censo 2022 | SIDRA tabela 9605 ou Microdados (complexo) | JSON/CSV |
| Taxa de vacância | IBGE Censo 2022 | SIDRA tabela 9672 | JSON |

### 4.4 IPEA — Atlas da Violência (Dimensão E)

| Dado | Fonte | URL | Formato |
|------|-------|-----|---------|
| Taxa de homicídios por município | IPEA Atlas da Violência 2023 | `https://www.ipea.gov.br/atlasviolencia/download/24/atlas-da-violencia-2023-microdados` | XLSX/CSV |

---

## 5. Contrato com o Banco de Dados

### Tabela `risk_geodata_layers` (existente — migration 006)

```sql
-- Colunas relevantes para carga:
id          UUID    PK (uuid_generate_v4())
layer_type  VARCHAR(40) NOT NULL   -- 'UC', 'TI', 'deslizamento', 'inundacao'
name        VARCHAR(200)           -- nome da área (ex: "APA Botucatu")
attributes  JSONB                  -- metadados extras (categoria, ato_legal, etc.)
source      VARCHAR(100) NOT NULL  -- 'ICMBio WFS 2023', 'CEMADEN 2022', etc.
geom        GEOMETRY(GEOMETRY, 4326)  -- PostGIS, SRID 4326
loaded_at   TIMESTAMPTZ  DEFAULT now()
```

**Estratégia de upsert:** DELETE WHERE layer_type = :type; INSERT novo batch. Mantém dados históricos em `loaded_at`.

### Tabela `ibge_municipality_stats` (existente — migration 006)

```sql
ibge_code           VARCHAR(7)  PK  -- código IBGE 7 dígitos
name                VARCHAR(100) NOT NULL
state               VARCHAR(2)  NOT NULL
idh                 NUMERIC(4,3)    -- ex: 0.750
homicide_rate       NUMERIC(6,2)    -- por 100k habitantes
population_2022     INTEGER
population_2010     INTEGER
avg_household_income NUMERIC(10,2)  -- R$/mês
vacancy_rate        NUMERIC(5,2)    -- %
updated_at          TIMESTAMPTZ DEFAULT now()
```

**Estratégia de upsert:** `INSERT ... ON CONFLICT (ibge_code) DO UPDATE SET ...`

### Arquivo `data/atlas_violencia.csv`

```
ibge_code,year,homicide_rate
1100015,2022,18.5
...
```

Carregado em memória por `IpeaAtlas` via `lru_cache`. Deve estar presente na imagem Docker ou baixado para GCS e copiado no container.

---

## 6. Arquitetura do Job

### Job: `jobs/load_geodata.py`

```text
Trigger: manual (gcloud run jobs execute radar-load-geodata)
         OU Cloud Scheduler mensal (dados mudam 1×/ano)

Fluxo:
  1. Para cada layer_type (UC, TI, deslizamento, inundacao):
     a. Download do GeoJSON/shapefile da URL pública
     b. Parse via geopandas (ou requests + json)
     c. Reprojetar para SRID 4326 se necessário
     d. Simplificar geometrias (tolerance=0.001°) para reduzir tamanho
     e. Upsert em bulk para risk_geodata_layers
     f. Log: camada carregada + contagem de polígonos

  2. Populara ibge_municipality_stats:
     a. Download malha municipal IBGE (ZIP → shapefile)
     b. Buscar população via IBGE SIDRA API
     c. Carregar IDH do XLSX Atlas Brasil (ou GCS se já disponível)
     d. Buscar renda e vacância via IBGE SIDRA API
     e. Upsert em bulk
     f. Log: municípios carregados

  3. Gerar data/atlas_violencia.csv:
     a. Download IPEA Atlas da Violência (XLSX)
     b. Extrair ibge_code + homicide_rate + year mais recente
     c. Salvar como data/atlas_violencia.csv
     d. Upload para GCS (gs://radar-raw/reference/atlas_violencia.csv)
     e. Log: municípios com taxa de homicídio
```

### Dependências Python (nova extra `geodata`)

| Pacote | Uso |
|--------|-----|
| `geopandas>=0.14` | Leitura e reprojeção de shapefiles |
| `shapely>=2.0` | Operações geométricas (simplificação) |
| `fiona>=1.9` | Backend de leitura de shapefiles para geopandas |
| `openpyxl>=3.1` | Leitura de XLSX (Atlas Brasil, IPEA) — já presente |
| `requests>=2.31` | Download de arquivos públicos — já presente |
| `psycopg2-binary>=2.9` | Bulk insert via COPY para performance — alternativa ao SQLAlchemy row-by-row |

---

## 7. Critérios de Aceite

| ID | Cenário | Resultado esperado |
|----|---------|-------------------|
| AT-001 | Job executa do zero (tabelas vazias) | `risk_geodata_layers` com ≥500 registros UC + ≥700 TI; `ibge_municipality_stats` com 5.570 linhas; `atlas_violencia.csv` presente |
| AT-002 | Job executa pela segunda vez (dados já existentes) | Sem duplicatas; contagens idênticas ou atualizadas; `loaded_at` refreshado |
| AT-003 | `IbamaLookup.contains_point(-15.78, -47.93, ['UC'])` após carga | Retorna lista não-vazia se ponto estiver dentro de UC (DF tem UCs federais) |
| AT-004 | `IbgeLookup.get_stats('5300108')` após carga | Retorna dict com `idh`, `population_2022`, `homicide_rate` não-nulos (Brasília) |
| AT-005 | `IpeaAtlas().get_homicide_rate('5300108')` após CSV gerado | Retorna float (taxa de Brasília) |
| AT-006 | WFS ICMBio indisponível durante carga | Job loga erro na camada UC, continua com TI/CEMADEN/IBGE; saída com `partial_layers=['UC']` |
| AT-007 | Execução completa no Cloud Run | Job finaliza em <30 min; exit(0); logs estruturados com contagem por camada |

---

## 8. Estratégia de Atualização

| Fonte | Frequência de atualização | Estratégia no job |
|-------|--------------------------|-------------------|
| UC/TI (IBAMA/FUNAI) | ~1×/ano (novos decretos) | Cloud Scheduler mensal; re-carga completa por layer_type |
| CEMADEN municípios | ~2×/ano | Cloud Scheduler bimestral; re-carga completa |
| IBGE população | 10 anos (próximo Censo: 2032) | Apenas atualização de estimativas anuais via SIDRA |
| IDH Atlas Brasil | Quinquenal | Atualização manual após publicação PNUD |
| IPEA Atlas Violência | Anual (publicado em junho) | Cloud Scheduler anual; re-geração do CSV |

---

## 9. Fora do Escopo

| Item | Motivo |
|------|--------|
| APP derivada de buffer hidrográfico | Alta complexidade; requer dados hidrográficos + cálculo de faixa por classe de rio |
| CEMADEN por setor de risco (subpolígonos dentro do município) | Download individual por município; 5.570 requests; fase futura |
| Dados IBGE por setor censitário (renda/vacância granular) | Microdados do Censo 2022 ainda em processamento; usar dados municipais por ora |
| Dados INCRA/SIGEF (imóveis rurais) | Escopo específico para Fase Rural (futura) |
| Certidões CETESB/INEA (contaminação) | Bases estaduais fragmentadas; cobertura parcial |

---

## 10. Dependências

| Dependência | Status |
|-------------|--------|
| Migration 006 aplicada (tabelas criadas) | ✅ Ativo no GCP (rodou via radar-migrate) |
| PostGIS habilitado no Cloud SQL | ✅ Já habilitado |
| Cloud Run Job `radar-load-geodata` criado | ❌ Pendente (criado nesta feature) |
| GCS bucket `radar-raw` com prefixo `reference/` | ✅ Bucket existe |
| ICMBio WFS acessível da Cloud Run | A validar (IP público GCP — WFS público) |
| IBGE SIDRA API acessível | ✅ API pública, sem autenticação |

---

## 11. Não-Funcionais

| Requisito | Valor |
|-----------|-------|
| Tempo máximo de carga | 30 min (job timeout: 3600s) |
| Memória Cloud Run | 2Gi (geopandas + shapefiles em memória) |
| Idempotência | Re-execução não duplica dados |
| Cobertura geográfica | 100% do território brasileiro |
| Resolução espacial mínima | Polígono municipal (não setor censitário nesta fase) |

---

**Clarity Score:** 15/15  
**Ready for:** `/design .claude/sdd/features/DEFINE_INGESTAO_GEODADOS_RISCO.md`
