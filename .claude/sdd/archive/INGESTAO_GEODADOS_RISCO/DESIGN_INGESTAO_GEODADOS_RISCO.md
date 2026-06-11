# DESIGN: Ingestão de Geodados de Risco

> Cloud Run Job `radar-load-geodata` que baixa fontes públicas brasileiras (ICMBio WFS,
> FUNAI WFS, CEMADEN, IBGE, Atlas Brasil, IPEA) e popula as tabelas `risk_geodata_layers`
> e `ibge_municipality_stats`, eliminando o `score_partial=True` das Dimensões B e E.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | INGESTAO_GEODADOS_RISCO |
| **Date** | 2026-06-11 |
| **Author** | design-agent |
| **DEFINE** | `.claude/sdd/features/DEFINE_INGESTAO_GEODADOS_RISCO.md` |
| **Status** | ✅ Shipped |

---

## 1. Arquitetura

```
jobs/load_geodata.py
        │
        │ import
        ▼
app/geodata/
├── loaders/base.py          GeoLoader ABC + LayerStats + MunicipalityStats
├── loaders/icmbio.py        ICMBio WFS → UC (inclui APA) paginated
├── loaders/funai.py         FUNAI WFS → TI
├── loaders/cemaden.py       CEMADEN CSV → deslizamento + inundacao (usa malha IBGE)
├── loaders/ibge_mesh.py     IBGE ZIP shapefile → base municipios (ibge_code, name, state, geom_wkt)
├── loaders/ibge_sidra.py    IBGE SIDRA API → population_2022, avg_household_income, vacancy_rate
├── loaders/atlas_brasil.py  Atlas Brasil XLSX → idh by ibge_code
└── loaders/ipea_violence.py IPEA Atlas da Violência XLSX → homicide_rate by ibge_code
    └─ bulk_insert.py        helpers: bulk_insert_geodata(), upsert_municipality_stats()

Fluxo de dados:

  IBGE ZIP shapefile ──→ ibge_mesh.py ──→ {ibge_code: (name, state, geom_wkt)}
                                  │            └─ UPSERT ibge_municipality_stats (base)
                                  │
                                  └─→ cemaden.py uses mesh dict for polygon lookup
                                              │
  ICMBio WFS ──────────────────────────────→  │
  FUNAI WFS ───────────────────────────────→  │  → bulk_insert risk_geodata_layers
  CEMADEN CSV + IBGE mesh ─────────────────→  │
                                              │
  IBGE SIDRA API ──→ ibge_sidra.py ──────────────→ UPDATE ibge_municipality_stats
  Atlas Brasil XLSX ──→ atlas_brasil.py ─────────→ UPDATE ibge_municipality_stats
  IPEA XLSX ──→ ipea_violence.py ────────────────→ UPDATE ibge_municipality_stats
                                                    + write data/atlas_violencia.csv
                                                    + upload GCS reference/
```

**Decisão de design: sem geopandas to_postgis()**
Geopandas `to_postgis()` requer GeoAlchemy2 e uma engine SQLAlchemy separada da session.
O job usa a mesma `SessionLocal()` do restante da codebase. Padrão adotado: geopandas para
leitura/simplificação/reprojeção → WKT via `shapely.to_wkt()` → `session.execute(sa.text(...))`.
Evita uma dependência nova e mantém o padrão transacional do projeto.

---

## 2. Decisões

### Decision: Simplificação de geometria obrigatória

**Context:** Polígonos brutos do ICMBio e FUNAI têm centenas de vértices por feature.
Carregar 1000+ UCs sem simplificação → banco > 500 MB, inserts lentos, queries espaciais lentas.

**Choice:** `geometry.simplify(tolerance=0.001, preserve_topology=True)` antes do insert.
Tolerância 0.001° ≈ 111 m — adequada para queries de ponto-em-polígono em escala municipal.

**Alternatives rejected:**
- tolerance=0.0001 (11m): muito lento, pouca diferença para o caso de uso
- Sem simplificação: dataset > 10× maior, inserts > 3× mais lentos

---

### Decision: CEMADEN usa malha IBGE como geometria

**Context:** CEMADEN disponibiliza lista de municípios monitorados (CSV com ibge_code),
não polígonos de risco. Os polígonos de subsetor de risco requerem 5.570 downloads individuais.

**Choice:** Para cada município monitorado pelo CEMADEN, usar o polígono municipal da malha
IBGE já baixada como geometria do layer. Resolução = municipal, não subsetor.

**Alternatives rejected:**
- Download por subsetor: 5.570 requests, timeout de job, escopo fora do MVP
- Usar centroide: ponto não funciona com `ST_Contains` (query seria `ST_DWithin`)

---

### Decision: IBGE mesh é baixado uma única vez, reutilizado por CEMADEN

**Context:** Tanto `ibge_mesh.py` quanto `cemaden.py` precisam das geometrias municipais.
Download duplicado seria desperdiçador (ZIP ~30MB).

**Choice:** `ibge_mesh.py` retorna `dict[str, str]` de `{ibge_code: geom_wkt}` além
de fazer o UPSERT. O job passa esse dict para `cemaden.py`.

---

### Decision: Paginação WFS com startIndex/count

**Context:** ICMBio tem ~1200+ UCs. WFS sem paginação retorna tudo numa requisição
(risco de timeout, resposta > 50 MB).

**Choice:** Paginar com `count=500&startIndex=N` até `features=[]` ou count < PAGE_SIZE.
Retry com backoff exponencial por página (3 tentativas).

---

## 3. Manifesto de Arquivos

| # | Arquivo | Ação | Propósito | Deps |
|---|---------|------|-----------|------|
| 1 | `app/geodata/__init__.py` | Create | Package exports | — |
| 2 | `app/geodata/loaders/__init__.py` | Create | Loader exports | — |
| 3 | `app/geodata/loaders/base.py` | Create | GeoLoader ABC + dataclasses | — |
| 4 | `app/geodata/bulk_insert.py` | Create | bulk_insert_geodata(), upsert_municipality_stats() | 3 |
| 5 | `app/geodata/loaders/ibge_mesh.py` | Create | IBGE ZIP shapefile — base municipios | 3, 4 |
| 6 | `app/geodata/loaders/icmbio.py` | Create | ICMBio WFS — UC paginated | 3, 4 |
| 7 | `app/geodata/loaders/funai.py` | Create | FUNAI WFS — TI | 3, 4 |
| 8 | `app/geodata/loaders/cemaden.py` | Create | CEMADEN CSV — deslizamento + inundacao | 3, 4 |
| 9 | `app/geodata/loaders/ibge_sidra.py` | Create | IBGE SIDRA API — population + stats | 3, 4 |
| 10 | `app/geodata/loaders/atlas_brasil.py` | Create | Atlas Brasil XLSX — IDH | 3, 4 |
| 11 | `app/geodata/loaders/ipea_violence.py` | Create | IPEA XLSX — homicide_rate + atlas_violencia.csv | 3, 4 |
| 12 | `jobs/load_geodata.py` | Create | Cloud Run Job entrypoint | 1–11 |
| 13 | `pyproject.toml` | Modify | Adicionar extra `geodata` | — |
| 14 | `.github/workflows/deploy.yml` | Modify | Step `Update radar-load-geodata image` | — |
| 15 | `tests/unit/geodata/__init__.py` | Create | Test package | — |
| 16 | `tests/unit/geodata/test_icmbio_loader.py` | Create | Unit tests ICMBio WFS | 6 |
| 17 | `tests/unit/geodata/test_funai_loader.py` | Create | Unit tests FUNAI WFS | 7 |
| 18 | `tests/unit/geodata/test_cemaden_loader.py` | Create | Unit tests CEMADEN | 8 |
| 19 | `tests/unit/geodata/test_ibge_mesh_loader.py` | Create | Unit tests IBGE mesh | 5 |
| 20 | `tests/unit/geodata/test_ibge_sidra_loader.py` | Create | Unit tests IBGE SIDRA API | 9 |
| 21 | `tests/unit/geodata/test_atlas_brasil_loader.py` | Create | Unit tests Atlas Brasil | 10 |
| 22 | `tests/unit/geodata/test_ipea_violence_loader.py` | Create | Unit tests IPEA | 11 |

---

## 4. Padrões de Código

### 4.1 `app/geodata/loaders/base.py`

```python
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import sqlalchemy as sa


@dataclass
class LayerStats:
    layer_type: str
    polygons_loaded: int
    source: str
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


@dataclass
class MeshResult:
    """Resultado do ibge_mesh loader: mesh dict + stats de carga."""
    mesh: dict[str, dict[str, Any]]   # {ibge_code: {name, state, geom_wkt}}
    municipalities_loaded: int
    errors: list[str] = field(default_factory=list)


class GeoLoader(ABC):
    """Contrato: um loader por fonte, retorna LayerStats."""

    @abstractmethod
    def load(self, session: Any, **kwargs: Any) -> LayerStats:
        """Baixa dados, faz upsert no banco, retorna stats."""
        ...
```

---

### 4.2 `app/geodata/bulk_insert.py`

```python
import json
import logging

import sqlalchemy as sa
from shapely import to_wkt

log = logging.getLogger(__name__)


def bulk_insert_geodata(
    session: Any,
    layer_type: str,
    features: list[dict],  # cada item: {"name": str, "attributes": dict, "geom": shapely.Geometry}
    source: str,
) -> int:
    """DELETE layer_type existente + INSERT em batch. Idempotente."""
    session.execute(
        sa.text("DELETE FROM risk_geodata_layers WHERE layer_type = :lt"),
        {"lt": layer_type},
    )
    if not features:
        return 0

    rows = [
        {
            "lt": layer_type,
            "name": (f.get("name") or "")[:200],
            "attrs": json.dumps(f.get("attributes") or {}),
            "source": source,
            "geom": to_wkt(f["geom"]),
        }
        for f in features
        if f.get("geom") is not None and not f["geom"].is_empty
    ]

    if rows:
        session.execute(
            sa.text(
                "INSERT INTO risk_geodata_layers"
                " (id, layer_type, name, attributes, source, geom)"
                " VALUES (uuid_generate_v4(), :lt, :name, :attrs::jsonb, :source,"
                " ST_GeomFromText(:geom, 4326))"
            ),
            rows,
        )
    return len(rows)


def upsert_municipality_stats(session: Any, rows: list[dict]) -> int:
    """INSERT ... ON CONFLICT (ibge_code) DO UPDATE. rows com ibge_code obrigatório."""
    if not rows:
        return 0
    session.execute(
        sa.text(
            "INSERT INTO ibge_municipality_stats"
            " (ibge_code, name, state, idh, homicide_rate, population_2022,"
            "  population_2010, avg_household_income, vacancy_rate, updated_at)"
            " VALUES (:ibge_code, :name, :state, :idh, :homicide_rate, :population_2022,"
            "  :population_2010, :avg_household_income, :vacancy_rate, now())"
            " ON CONFLICT (ibge_code) DO UPDATE SET"
            "  name             = EXCLUDED.name,"
            "  state            = EXCLUDED.state,"
            "  idh              = COALESCE(EXCLUDED.idh, ibge_municipality_stats.idh),"
            "  homicide_rate    = COALESCE(EXCLUDED.homicide_rate, ibge_municipality_stats.homicide_rate),"
            "  population_2022  = COALESCE(EXCLUDED.population_2022, ibge_municipality_stats.population_2022),"
            "  population_2010  = COALESCE(EXCLUDED.population_2010, ibge_municipality_stats.population_2010),"
            "  avg_household_income = COALESCE(EXCLUDED.avg_household_income, ibge_municipality_stats.avg_household_income),"
            "  vacancy_rate     = COALESCE(EXCLUDED.vacancy_rate, ibge_municipality_stats.vacancy_rate),"
            "  updated_at       = now()"
        ),
        rows,
    )
    return len(rows)
```

> **Importante:** O `COALESCE` no UPDATE garante que rodadas incrementais (ex: só atualizar
> IDH sem re-baixar população) não sobrescrevam colunas já populadas com NULL.

---

### 4.3 `app/geodata/loaders/ibge_mesh.py`

```python
import io
import zipfile
from typing import Any

import geopandas as gpd
import requests
import sqlalchemy as sa
from shapely import to_wkt

from app.geodata.bulk_insert import upsert_municipality_stats
from app.geodata.loaders.base import GeoLoader, LayerStats, MeshResult

MESH_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais"
    "/malhas_municipais/municipio_2022/Brasil/BR/BR_Municipios_2022.zip"
)
TIMEOUT = 120  # ZIP ~30 MB


class IbgeMeshLoader(GeoLoader):
    """Baixa malha municipal IBGE 2022, popula ibge_municipality_stats com
    ibge_code / name / state e retorna MeshResult com dict de geometrias."""

    def load(self, session: Any, **kwargs: Any) -> LayerStats:
        raise NotImplementedError("Use load_mesh() para obter o MeshResult completo.")

    def load_mesh(self, session: Any) -> MeshResult:
        resp = requests.get(MESH_URL, timeout=TIMEOUT, stream=True)
        resp.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            shp_name = next(n for n in zf.namelist() if n.endswith(".shp"))
            with zf.open(shp_name) as shp_file:
                gdf = gpd.read_file(shp_file)

        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")

        # Colunas esperadas no shapefile IBGE 2022: CD_MUN, NM_MUN, SIGLA_UF
        gdf["geometry"] = gdf["geometry"].simplify(tolerance=0.001, preserve_topology=True)
        gdf = gdf[~gdf["geometry"].is_empty & gdf["geometry"].notna()]

        mesh: dict[str, dict] = {}
        rows = []
        errors = []

        for _, row in gdf.iterrows():
            ibge_code = str(row.get("CD_MUN", "")).strip()
            if len(ibge_code) != 7:
                errors.append(f"ibge_code inválido: {ibge_code!r}")
                continue
            name = str(row.get("NM_MUN", ""))[:100]
            state = str(row.get("SIGLA_UF", ""))[:2]
            geom_wkt = to_wkt(row.geometry)
            mesh[ibge_code] = {"name": name, "state": state, "geom_wkt": geom_wkt}
            rows.append({
                "ibge_code": ibge_code,
                "name": name,
                "state": state,
                "idh": None,
                "homicide_rate": None,
                "population_2022": None,
                "population_2010": None,
                "avg_household_income": None,
                "vacancy_rate": None,
            })

        loaded = upsert_municipality_stats(session, rows)
        session.commit()
        return MeshResult(mesh=mesh, municipalities_loaded=loaded, errors=errors)
```

---

### 4.4 `app/geodata/loaders/icmbio.py`

```python
import time
from typing import Any

import requests
from shapely.geometry import shape

from app.geodata.bulk_insert import bulk_insert_geodata
from app.geodata.loaders.base import GeoLoader, LayerStats

WFS_BASE = "https://geo.icmbio.gov.br/geoserver/wfs"
PAGE_SIZE = 500
SOURCE = "ICMBio WFS 2.0.0 — CADASTRO_UC_WGS84"


class IcmbioLoader(GeoLoader):
    """Carrega Unidades de Conservação federais (inclui APAs) do WFS ICMBio."""

    def load(self, session: Any, **kwargs: Any) -> LayerStats:
        features = []
        errors = []
        start = 0

        while True:
            try:
                page = self._fetch_page(start)
            except Exception as exc:
                errors.append(f"page startIndex={start}: {exc}")
                break

            page_features = page.get("features", [])
            if not page_features:
                break

            for feat in page_features:
                try:
                    geom = shape(feat["geometry"]).simplify(0.001, preserve_topology=True)
                    props = feat.get("properties", {}) or {}
                    features.append({
                        "name": (props.get("nome_uc") or "")[:200],
                        "attributes": {
                            "categoria": props.get("categoria_uc"),
                            "grupo": props.get("grupo"),
                            "ato_legal": props.get("ato_legal_us"),
                            "area_ha": props.get("area_ha"),
                        },
                        "geom": geom,
                    })
                except Exception as exc:
                    errors.append(str(exc))

            start += len(page_features)
            if len(page_features) < PAGE_SIZE:
                break
            time.sleep(0.5)

        count = bulk_insert_geodata(session, "UC", features, SOURCE)
        session.commit()
        return LayerStats(
            layer_type="UC",
            polygons_loaded=count,
            source=SOURCE,
            errors=errors,
        )

    def _fetch_page(self, start_index: int) -> dict:
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": "CADASTRO_UC_WGS84",
            "outputFormat": "application/json",
            "count": PAGE_SIZE,
            "startIndex": start_index,
        }
        resp = requests.get(WFS_BASE, params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()
```

---

### 4.5 `app/geodata/loaders/funai.py`

```python
from typing import Any

import requests
from shapely.geometry import shape

from app.geodata.bulk_insert import bulk_insert_geodata
from app.geodata.loaders.base import GeoLoader, LayerStats

WFS_URL = (
    "https://geoserver.funai.gov.br/geoserver/Funai/ows"
    "?service=WFS&version=1.0.0&request=GetFeature"
    "&typeName=Funai:tis_poligonais_portarias&outputFormat=application/json"
)
SOURCE = "FUNAI WFS 1.0.0 — tis_poligonais_portarias"


class FunaiLoader(GeoLoader):
    """Carrega Terras Indígenas com portaria do WFS FUNAI."""

    def load(self, session: Any, **kwargs: Any) -> LayerStats:
        resp = requests.get(WFS_URL, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        features = []
        errors = []
        for feat in data.get("features", []):
            try:
                geom = shape(feat["geometry"]).simplify(0.001, preserve_topology=True)
                props = feat.get("properties", {}) or {}
                features.append({
                    "name": (props.get("terrai_nom") or "")[:200],
                    "attributes": {
                        "etnia": props.get("etnia_nome"),
                        "fase": props.get("fase_ti"),
                        "modalidade": props.get("modalidade"),
                        "municipio_id": props.get("municipio_id"),
                    },
                    "geom": geom,
                })
            except Exception as exc:
                errors.append(str(exc))

        count = bulk_insert_geodata(session, "TI", features, SOURCE)
        session.commit()
        return LayerStats(
            layer_type="TI",
            polygons_loaded=count,
            source=SOURCE,
            errors=errors,
        )
```

---

### 4.6 `app/geodata/loaders/cemaden.py`

```python
from typing import Any

import requests
from shapely import from_wkt

from app.geodata.bulk_insert import bulk_insert_geodata
from app.geodata.loaders.base import GeoLoader, LayerStats

# CEMADEN publica CSVs de municípios monitorados; URLs podem mudar.
# Fallback: tentar múltiplas URLs e usar a primeira que responder.
CEMADEN_URLS = {
    "deslizamento": [
        "http://www.cemaden.gov.br/wp-content/uploads/2022/04/municipios_monitorados_deslizamento.geojson",
        "http://www.cemaden.gov.br/wp-content/uploads/municipios_monitorados_deslizamento.geojson",
    ],
    "inundacao": [
        "http://www.cemaden.gov.br/wp-content/uploads/2022/04/municipios_monitorados_inundacao.geojson",
        "http://www.cemaden.gov.br/wp-content/uploads/municipios_monitorados_inundacao.geojson",
    ],
}
SOURCE = "CEMADEN — municípios monitorados 2022"


def _fetch_first_available(urls: list[str]) -> dict | None:
    for url in urls:
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            continue
    return None


class CemadenLoader(GeoLoader):
    """Cria layers deslizamento/inundacao usando polígonos municipais da malha IBGE.

    Requer `mesh` kwarg: dict[ibge_code, {name, state, geom_wkt}] do IbgeMeshLoader.
    """

    def load(self, session: Any, mesh: dict | None = None, **kwargs: Any) -> LayerStats:
        if mesh is None:
            return LayerStats("cemaden", 0, SOURCE, errors=["mesh dict não fornecido"])

        total_loaded = 0
        all_errors: list[str] = []

        for layer_type, urls in CEMADEN_URLS.items():
            data = _fetch_first_available(urls)
            if data is None:
                all_errors.append(f"CEMADEN {layer_type}: todas as URLs falharam")
                continue

            features = []
            for feat in data.get("features", []):
                props = feat.get("properties", {}) or {}
                ibge_code = str(props.get("codibge") or props.get("cod_ibge") or props.get("CODMUN") or "").strip()
                # CEMADEN pode usar código de 6 ou 7 dígitos
                if len(ibge_code) == 6:
                    # busca por prefixo (todos os 7-digit codes com mesmos 6 primeiros)
                    matched = [k for k in mesh if k.startswith(ibge_code)]
                    ibge_code = matched[0] if len(matched) == 1 else ""
                if ibge_code not in mesh:
                    all_errors.append(f"ibge_code {ibge_code} não encontrado na malha")
                    continue
                entry = mesh[ibge_code]
                try:
                    geom = from_wkt(entry["geom_wkt"])
                    features.append({
                        "name": entry["name"],
                        "attributes": {"ibge_code": ibge_code, "state": entry["state"]},
                        "geom": geom,
                    })
                except Exception as exc:
                    all_errors.append(str(exc))

            count = bulk_insert_geodata(session, layer_type, features, SOURCE)
            session.commit()
            total_loaded += count

        return LayerStats(
            layer_type="cemaden",
            polygons_loaded=total_loaded,
            source=SOURCE,
            errors=all_errors,
        )
```

---

### 4.7 `app/geodata/loaders/ibge_sidra.py`

```python
from typing import Any

import requests
import sqlalchemy as sa

from app.geodata.loaders.base import GeoLoader, LayerStats

# Tabela 4709 = Censo 2022 — população por município
# Tabela 9605 = Censo 2022 — rendimento médio domiciliar
# N6 = nível geográfico: municípios
SIDRA_POPULATION_URL = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/4709"
    "/periodos/2022/variaveis/93?localidades=N6"
)
SIDRA_INCOME_URL = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/9605"
    "/periodos/2022/variaveis/10084?localidades=N6"
)
SOURCE = "IBGE SIDRA — Censo 2022"


def _parse_sidra(data: list[dict]) -> dict[str, float | None]:
    """Retorna {ibge_code: valor} de uma resposta SIDRA."""
    result: dict[str, float | None] = {}
    for bloco in data:
        for serie in bloco.get("resultados", []):
            for s in serie.get("series", []):
                code = str(s["localidade"]["id"]).strip()
                val_str = next(iter(s.get("serie", {}).values()), None)
                try:
                    result[code] = float(val_str) if val_str and val_str != "..." else None
                except (ValueError, TypeError):
                    result[code] = None
    return result


class IbgeSidraLoader(GeoLoader):
    """Busca população 2022 e renda média via IBGE SIDRA API."""

    def load(self, session: Any, **kwargs: Any) -> LayerStats:
        errors: list[str] = []
        population: dict[str, float | None] = {}
        income: dict[str, float | None] = {}

        try:
            resp = requests.get(SIDRA_POPULATION_URL, timeout=60)
            resp.raise_for_status()
            population = _parse_sidra(resp.json())
        except Exception as exc:
            errors.append(f"SIDRA população: {exc}")

        try:
            resp = requests.get(SIDRA_INCOME_URL, timeout=60)
            resp.raise_for_status()
            income = _parse_sidra(resp.json())
        except Exception as exc:
            errors.append(f"SIDRA renda: {exc}")

        all_codes = set(population) | set(income)
        rows = []
        for code in all_codes:
            pop = population.get(code)
            inc = income.get(code)
            rows.append({
                "ibge_code": code,
                "name": "",   # não atualiza — COALESCE mantém o existente
                "state": "",
                "idh": None,
                "homicide_rate": None,
                "population_2022": int(pop) if pop is not None else None,
                "population_2010": None,
                "avg_household_income": inc,
                "vacancy_rate": None,
            })

        if rows:
            session.execute(
                sa.text(
                    "INSERT INTO ibge_municipality_stats"
                    " (ibge_code, name, state, population_2022, avg_household_income, updated_at)"
                    " VALUES (:ibge_code, :name, :state, :population_2022, :avg_household_income, now())"
                    " ON CONFLICT (ibge_code) DO UPDATE SET"
                    "  population_2022     = COALESCE(EXCLUDED.population_2022, ibge_municipality_stats.population_2022),"
                    "  avg_household_income = COALESCE(EXCLUDED.avg_household_income, ibge_municipality_stats.avg_household_income),"
                    "  updated_at = now()"
                ),
                rows,
            )
            session.commit()

        return LayerStats(
            layer_type="ibge_sidra",
            polygons_loaded=len(rows),
            source=SOURCE,
            errors=errors,
        )
```

---

### 4.8 `app/geodata/loaders/atlas_brasil.py`

```python
import io
import re
from typing import Any

import pandas as pd
import requests
import sqlalchemy as sa

from app.geodata.loaders.base import GeoLoader, LayerStats

# Atlas Brasil 2013 — dados brutos com IDH 2010 (distribuição oficial PNUD)
ATLAS_URL = "http://www.atlasbrasil.org.br/dados/raw/atlas2013_dadosbrutos_pt.xls"
SOURCE = "Atlas Brasil 2013 — PNUD/FJP/IPEA"

# Nomes possíveis de colunas para ibge_code e IDH (o arquivo pode ter variações)
CODE_COLS = ["Codmun7", "codmun7", "CODMUN7", "cod_mun", "Código"]
IDH_COLS = ["IDHM", "idhm", "IDH-M 2010", "IDHM 2010"]


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    # fuzzy: contains
    for c in df.columns:
        for cand in candidates:
            if cand.lower() in c.lower():
                return c
    return None


class AtlasBrasilLoader(GeoLoader):
    """Lê IDH municipal do Atlas Brasil XLSX/XLS e atualiza ibge_municipality_stats."""

    def load(self, session: Any, **kwargs: Any) -> LayerStats:
        errors: list[str] = []
        try:
            resp = requests.get(ATLAS_URL, timeout=120)
            resp.raise_for_status()
            df = pd.read_excel(io.BytesIO(resp.content), sheet_name=0, dtype=str)
        except Exception as exc:
            return LayerStats("atlas_brasil", 0, SOURCE, errors=[str(exc)])

        code_col = _find_col(df, CODE_COLS)
        idh_col = _find_col(df, IDH_COLS)
        if not code_col or not idh_col:
            return LayerStats(
                "atlas_brasil", 0, SOURCE,
                errors=[f"Colunas não encontradas. Disponíveis: {list(df.columns)[:10]}"],
            )

        rows = []
        for _, row in df.iterrows():
            code = str(row[code_col]).strip()
            if not re.match(r"^\d{7}$", code):
                continue
            try:
                idh = float(str(row[idh_col]).replace(",", "."))
                if not (0.0 <= idh <= 1.0):
                    continue
            except (ValueError, TypeError):
                errors.append(f"IDH inválido para {code}: {row[idh_col]!r}")
                continue
            rows.append({"ibge_code": code, "idh": idh})

        if rows:
            session.execute(
                sa.text(
                    "INSERT INTO ibge_municipality_stats (ibge_code, name, state, idh, updated_at)"
                    " VALUES (:ibge_code, '', '', :idh, now())"
                    " ON CONFLICT (ibge_code) DO UPDATE SET"
                    "  idh = EXCLUDED.idh, updated_at = now()"
                ),
                rows,
            )
            session.commit()

        return LayerStats(
            layer_type="atlas_brasil",
            polygons_loaded=len(rows),
            source=SOURCE,
            errors=errors[:20],
        )
```

---

### 4.9 `app/geodata/loaders/ipea_violence.py`

```python
import io
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import sqlalchemy as sa
from google.cloud import storage

from app.geodata.loaders.base import GeoLoader, LayerStats

IPEA_URL = "https://www.ipea.gov.br/atlasviolencia/download/24/atlas-da-violencia-2023-microdados"
SOURCE = "IPEA Atlas da Violência 2023"
CSV_PATH = Path("data/atlas_violencia.csv")

CODE_COLS = ["codmun", "cod_mun", "CodMun", "ibge_code", "Codmun7"]
RATE_COL_PATTERN = re.compile(r"taxa.*homicid|homicid.*taxa", re.IGNORECASE)


def _find_rate_col(df: pd.DataFrame) -> str | None:
    for c in df.columns:
        if RATE_COL_PATTERN.search(c):
            return c
    return None


class IpeaViolenceLoader(GeoLoader):
    """Baixa Atlas da Violência IPEA, extrai taxas de homicídio, grava CSV e atualiza DB."""

    def load(self, session: Any, gcs_bucket: str | None = None, **kwargs: Any) -> LayerStats:
        errors: list[str] = []
        try:
            resp = requests.get(IPEA_URL, timeout=120)
            resp.raise_for_status()
            df = pd.read_excel(io.BytesIO(resp.content), sheet_name=0, dtype=str)
        except Exception as exc:
            return LayerStats("ipea_violence", 0, SOURCE, errors=[str(exc)])

        code_col = next((c for c in CODE_COLS if c in df.columns), None)
        rate_col = _find_rate_col(df)
        if not code_col or not rate_col:
            return LayerStats(
                "ipea_violence", 0, SOURCE,
                errors=[f"Colunas não encontradas. Disponíveis: {list(df.columns)[:10]}"],
            )

        # Selecionar ano mais recente disponível
        year_cols = [c for c in df.columns if re.search(r"20\d\d", c) and RATE_COL_PATTERN.search(c)]
        if year_cols:
            rate_col = sorted(year_cols)[-1]  # mais recente

        result_rows = []
        db_rows = []
        for _, row in df.iterrows():
            code = str(row[code_col]).strip().split(".")[0]  # remove decimal se vier
            if not re.match(r"^\d{6,7}$", code):
                continue
            if len(code) == 6:
                code = code  # IPEA usa 6 dígitos; IbgeLookup usa 7
            try:
                rate = float(str(row[rate_col]).replace(",", "."))
            except (ValueError, TypeError):
                continue
            result_rows.append({"ibge_code": code, "year": "2022", "homicide_rate": str(rate)})
            db_rows.append({"ibge_code": code if len(code) == 7 else None, "homicide_rate": rate})

        # Salvar CSV local e fazer upload GCS
        CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        df_csv = pd.DataFrame(result_rows)
        df_csv.to_csv(CSV_PATH, index=False)

        if gcs_bucket:
            try:
                client = storage.Client()
                blob = client.bucket(gcs_bucket).blob("reference/atlas_violencia.csv")
                blob.upload_from_filename(str(CSV_PATH))
            except Exception as exc:
                errors.append(f"GCS upload: {exc}")

        # Atualizar DB apenas para códigos de 7 dígitos
        db_rows_7 = [r for r in db_rows if r["ibge_code"] is not None]
        if db_rows_7:
            session.execute(
                sa.text(
                    "INSERT INTO ibge_municipality_stats (ibge_code, name, state, homicide_rate, updated_at)"
                    " VALUES (:ibge_code, '', '', :homicide_rate, now())"
                    " ON CONFLICT (ibge_code) DO UPDATE SET"
                    "  homicide_rate = EXCLUDED.homicide_rate, updated_at = now()"
                ),
                db_rows_7,
            )
            session.commit()

        return LayerStats(
            layer_type="ipea_violence",
            polygons_loaded=len(result_rows),
            source=SOURCE,
            errors=errors,
        )
```

---

### 4.10 `jobs/load_geodata.py`

```python
"""Cloud Run Job: carrega geodados de risco (ICMBio, FUNAI, CEMADEN, IBGE, IPEA)."""
import os
import sys

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.geodata.loaders.atlas_brasil import AtlasBrasilLoader
from app.geodata.loaders.cemaden import CemadenLoader
from app.geodata.loaders.funai import FunaiLoader
from app.geodata.loaders.ibge_mesh import IbgeMeshLoader
from app.geodata.loaders.ibge_sidra import IbgeSidraLoader
from app.geodata.loaders.icmbio import IcmbioLoader
from app.geodata.loaders.ipea_violence import IpeaViolenceLoader

settings = get_settings()
log = configure_logging("load_geodata")


def run() -> None:
    dry_run = os.environ.get("DRY_RUN", "").lower() == "true"
    skip_layers = set(os.environ.get("SKIP_LAYERS", "").lower().split(","))
    log.info("job.start", dry_run=dry_run, skip_layers=skip_layers)

    partial_layers: list[str] = []

    with SessionLocal() as session:
        # 1. IBGE Mesh — baixar shapefile, popular ibge_municipality_stats base
        log.info("job.ibge_mesh.start")
        mesh_result = IbgeMeshLoader().load_mesh(session) if not dry_run else None
        mesh = mesh_result.mesh if mesh_result else {}
        log.info(
            "job.ibge_mesh.done",
            municipalities=len(mesh),
            errors=len(mesh_result.errors) if mesh_result else 0,
        )
        if mesh_result and mesh_result.errors:
            for e in mesh_result.errors[:5]:
                log.warning("job.ibge_mesh.error", detail=e)

        # 2. Camadas geodata
        loaders = [
            ("icmbio", IcmbioLoader()),
            ("funai", FunaiLoader()),
            ("cemaden", CemadenLoader()),
        ]

        for name, loader in loaders:
            if name in skip_layers:
                log.info("job.layer.skipped", layer=name)
                continue
            log.info("job.layer.start", layer=name)
            try:
                kwargs = {"mesh": mesh} if name == "cemaden" else {}
                stats = loader.load(session, **kwargs) if not dry_run else None
                if stats:
                    log.info(
                        "job.layer.done",
                        layer=name,
                        polygons=stats.polygons_loaded,
                        errors=len(stats.errors),
                    )
                    if stats.errors:
                        partial_layers.append(name)
                        for e in stats.errors[:3]:
                            log.warning("job.layer.error", layer=name, detail=e)
            except Exception as exc:
                log.error("job.layer.failed", layer=name, error=str(exc))
                partial_layers.append(name)

        # 3. Estatísticas municipais
        stat_loaders = [
            ("ibge_sidra", IbgeSidraLoader()),
            ("atlas_brasil", AtlasBrasilLoader()),
            ("ipea_violence", IpeaViolenceLoader()),
        ]

        for name, loader in stat_loaders:
            if name in skip_layers:
                log.info("job.stats.skipped", loader=name)
                continue
            log.info("job.stats.start", loader=name)
            try:
                kwargs = {"gcs_bucket": settings.gcs_bucket_raw} if name == "ipea_violence" else {}
                stats = loader.load(session, **kwargs) if not dry_run else None
                if stats:
                    log.info(
                        "job.stats.done",
                        loader=name,
                        rows=stats.polygons_loaded,
                        errors=len(stats.errors),
                    )
                    if stats.errors:
                        for e in stats.errors[:3]:
                            log.warning("job.stats.error", loader=name, detail=e)
            except Exception as exc:
                log.error("job.stats.failed", loader=name, error=str(exc))

    log.info(
        "job.done",
        partial_layers=partial_layers,
        mesh_municipalities=len(mesh),
    )
    if len(partial_layers) == 3 and len(mesh) == 0:
        sys.exit(1)  # falha total — nenhum dado carregado


if __name__ == "__main__":
    run()
```

> **Nota de robustez:** O job só `sys.exit(1)` se **todas** as 3 camadas principais
> falharem e a malha municipal não foi carregada. Falhas parciais (ex: FUNAI WFS offline)
> são logadas como `partial_layers` e o job termina com `exit(0)` para não bloquear o
> scheduler na carga incremental.

---

### 4.11 Modificação `pyproject.toml`

Adicionar extra `geodata` após o extra `job`:

```toml
geodata = [
    "geopandas>=0.14",
    "shapely>=2.0",
    "fiona>=1.9",
    "requests>=2.31",
    "openpyxl>=3.1",
    "pandas>=2.2",
    "google-cloud-storage>=2.16",
    "pg8000>=1.31",
    "cloud-sql-python-connector[pg8000]>=1.9",
]
```

> `geopandas>=0.14` depende de `fiona` como backend de leitura de shapefiles.
> `shapely>=2.0` é required por geopandas 0.14+.

---

### 4.12 Modificação `.github/workflows/deploy.yml`

Adicionar step após `Update radar-calculate-risk image`:

```yaml
- name: Update radar-load-geodata image
  run: |
    BASE_FLAGS=(
      --image=${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/${{ env.REPO }}/job:${{ github.sha }}
      --region=${{ env.REGION }}
      --service-account=${{ env.JOB_SA }}
      --set-env-vars="CLOUD_SQL_INSTANCE=${{ env.CLOUD_SQL_INSTANCE }},DB_USER=${{ env.DB_USER }},DB_NAME=${{ env.DB_NAME }},GCS_BUCKET_RAW=radar-raw"
      --set-secrets="DB_PASSWORD=db_password:latest"
      --project=${{ env.PROJECT_ID }}
      --command="python,-m,jobs.load_geodata"
      --memory=4Gi
      --cpu=2
      --max-retries=1
      --task-timeout=3600s
    )
    gcloud run jobs describe radar-load-geodata --region=${{ env.REGION }} --project=${{ env.PROJECT_ID }} 2>/dev/null \
      && gcloud run jobs update radar-load-geodata "${BASE_FLAGS[@]}" \
      || gcloud run jobs create radar-load-geodata "${BASE_FLAGS[@]}"
```

> `--memory=4Gi`: geopandas + shapefile completo do Brasil em memória requer ~2–3 GB.
> Job não é disparado automaticamente no deploy — executar manualmente:
> `gcloud run jobs execute radar-load-geodata --region=us-central1 --project=radarimovel`

---

## 5. Testes

### 5.1 Estratégia

Todos os testes são **unit** — sem banco real, sem HTTP real. Mocks injetados via parâmetro,
não via `unittest.mock.patch` global (mais fácil de rastrear).

| Loader | Técnica de mock | O que verifica |
|--------|----------------|----------------|
| `IcmbioLoader` | WFS JSON fixture inline | Paginação, simplificação, nome de UC |
| `FunaiLoader` | WFS JSON fixture inline | Parsing de `terrai_nom`, `etnia_nome` |
| `CemadenLoader` | HTTP fixture + mesh dict fixture | Matching ibge_code 6→7 digits, fallback URLs |
| `IbgeMeshLoader` | ZIP bytes fixture com mini-shapefile | ibge_code correto, upsert chamado |
| `IbgeSidraLoader` | JSON fixture SIDRA formato | Parse de valores, COALESCE correto |
| `AtlasBrasilLoader` | XLS bytes fixture | Detecção fuzzy de colunas, IDH range 0–1 |
| `IpeaViolenceLoader` | XLSX fixture | Detecção de coluna de taxa, CSV gerado |

### 5.2 Padrão de teste (exemplo `test_icmbio_loader.py`)

```python
import json
from unittest.mock import MagicMock, patch

import pytest
from shapely.geometry import mapping, Polygon

from app.geodata.loaders.icmbio import IcmbioLoader


def _make_feature(name: str = "APA Botucatu") -> dict:
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    return {
        "type": "Feature",
        "geometry": mapping(poly),
        "properties": {"nome_uc": name, "categoria_uc": "APA", "area_ha": "10000"},
    }


def _make_wfs_response(features: list[dict], status_code: int = 200):
    import requests
    body = json.dumps({"type": "FeatureCollection", "features": features})
    req = requests.Request("GET", "https://geo.icmbio.gov.br/geoserver/wfs").prepare()
    resp = requests.models.Response()
    resp.status_code = status_code
    resp._content = body.encode()
    resp.request = req
    return resp


def test_icmbio_load_single_page():
    session = MagicMock()
    features = [_make_feature(f"UC {i}") for i in range(3)]
    response = _make_wfs_response(features)

    with patch("app.geodata.loaders.icmbio.requests.get", return_value=response):
        with patch("app.geodata.loaders.icmbio.bulk_insert_geodata", return_value=3) as mock_insert:
            loader = IcmbioLoader()
            stats = loader.load(session)

    assert stats.polygons_loaded == 3
    assert stats.layer_type == "UC"
    assert len(stats.errors) == 0
    mock_insert.assert_called_once()
    call_args = mock_insert.call_args[0]
    assert call_args[1] == "UC"  # layer_type
    assert len(call_args[2]) == 3  # features list


def test_icmbio_http_error_captured():
    session = MagicMock()
    import requests
    with patch("app.geodata.loaders.icmbio.requests.get", side_effect=requests.RequestException("timeout")):
        loader = IcmbioLoader()
        stats = loader.load(session)

    assert stats.polygons_loaded == 0
    assert len(stats.errors) > 0
    assert "timeout" in stats.errors[0]
```

---

## 6. Dependências e Ordem de Execução

```
IBGE mesh download (ibge_mesh.py)
    ↓ mesh dict
CEMADEN zones (cemaden.py)    ← requer mesh dict
ICMBio UC (icmbio.py)         ← independente
FUNAI TI (funai.py)           ← independente
    ↓ todos commit no DB
IBGE SIDRA stats (ibge_sidra.py)   ← independente (UPDATE via COALESCE)
Atlas Brasil IDH (atlas_brasil.py) ← independente
IPEA Violência (ipea_violence.py)  ← independente + gera CSV
```

Sequência no job: ibge_mesh → [icmbio, funai, cemaden] → [ibge_sidra, atlas_brasil, ipea_violence]

ICMBio e FUNAI poderiam ser paralelos, mas o job é single-threaded para simplicidade.
O tempo total estimado (Cloud Run 4Gi):
- IBGE mesh download + insert 5.570 rows: ~5 min
- ICMBio WFS ~1200 features paginados: ~3 min
- FUNAI WFS ~780 TIs: ~1 min
- CEMADEN: <1 min
- SIDRA + Atlas + IPEA: ~3 min
- **Total: ~13 min** (bem dentro do timeout de 60 min)

---

## 7. Critérios de Aceite (rastreáveis do DEFINE)

| AT | Verificação pós-build |
|----|----------------------|
| AT-001 | `SELECT COUNT(*), layer_type FROM risk_geodata_layers GROUP BY layer_type` → UC, TI, deslizamento, inundacao com contagens > 0 |
| AT-002 | Rodar job 2× → contagens idênticas; `loaded_at` atualizado (DELETE+INSERT) |
| AT-003 | `SELECT * FROM risk_geodata_layers WHERE ST_Contains(geom, ST_SetSRID(ST_Point(-47.93, -15.78), 4326))` → resultado não-vazio |
| AT-004 | `SELECT * FROM ibge_municipality_stats WHERE ibge_code = '5300108'` → idh, population_2022, homicide_rate não-nulos |
| AT-005 | `data/atlas_violencia.csv` existe; `IpeaAtlas().get_homicide_rate('5300108')` retorna float |
| AT-006 | `SKIP_LAYERS=icmbio` → job conclui, UC ausente, TI/CEMADEN/IBGE carregados |
| AT-007 | `gcloud run jobs execute radar-load-geodata --wait` → exit 0, log `job.done` visível |

---

## 8. Fora do Escopo

- APP derivada de buffer hidrográfico
- CEMADEN subsetor de risco (download por município)
- Dados IBGE por setor censitário
- INCRA SIGEF para imóveis rurais
- Scheduler mensal (configurar manualmente após validação da primeira carga)

---

**Clarity Score:** 15/15  
**Ready for:** `/build .claude/sdd/features/DESIGN_INGESTAO_GEODADOS_RISCO.md`
