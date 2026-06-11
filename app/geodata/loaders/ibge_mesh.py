import io
import os
import tempfile
import zipfile
from typing import Any

import geopandas as gpd
import requests
from shapely import to_wkt

from app.geodata.bulk_insert import upsert_municipality_stats
from app.geodata.loaders.base import GeoLoader, LayerStats, MeshResult

MESH_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais"
    "/malhas_municipais/municipio_2022/Brasil/BR/BR_Municipios_2022.zip"
)
TIMEOUT = 120


class IbgeMeshLoader(GeoLoader):
    """Downloads IBGE 2022 municipal shapefile, populates ibge_municipality_stats base rows,
    and returns a mesh dict {ibge_code: {name, state, geom_wkt}} for use by CemadenLoader."""

    def load(self, session: Any, **kwargs: Any) -> LayerStats:
        result = self.load_mesh(session)
        return LayerStats(
            layer_type="ibge_mesh",
            polygons_loaded=result.municipalities_loaded,
            source="IBGE Malha Municipal 2022",
            errors=result.errors,
        )

    def load_mesh(self, session: Any) -> MeshResult:
        resp = requests.get(MESH_URL, timeout=TIMEOUT, stream=True)
        resp.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            shp_name = next(n for n in zf.namelist() if n.endswith(".shp"))
            with tempfile.TemporaryDirectory() as tmpdir:
                base = os.path.splitext(shp_name)[0]
                for name in zf.namelist():
                    if name.startswith(base):
                        zf.extract(name, tmpdir)
                gdf = gpd.read_file(os.path.join(tmpdir, shp_name))

        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")

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
            rows.append(
                {
                    "ibge_code": ibge_code,
                    "name": name,
                    "state": state,
                    "idh": None,
                    "homicide_rate": None,
                    "population_2022": None,
                    "population_2010": None,
                    "avg_household_income": None,
                    "vacancy_rate": None,
                }
            )

        loaded = upsert_municipality_stats(session, rows)
        session.commit()
        return MeshResult(mesh=mesh, municipalities_loaded=loaded, errors=errors)
