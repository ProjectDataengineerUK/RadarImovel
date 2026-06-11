from typing import Any

import requests
from shapely import from_wkt

from app.geodata.bulk_insert import bulk_insert_geodata
from app.geodata.loaders.base import GeoLoader, LayerStats

# CEMADEN publishes lists of monitored municipalities; URLs may change between updates.
CEMADEN_URLS: dict[str, list[str]] = {
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

# Property names CEMADEN has used across releases for the municipality IBGE code
_CODE_PROPS = ("codibge", "cod_ibge", "CODMUN", "geocodigo", "CD_MUN")


def _fetch_first_available(urls: list[str]) -> dict | None:
    for url in urls:
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            continue
    return None


def _extract_ibge_code(props: dict) -> str:
    for key in _CODE_PROPS:
        val = props.get(key)
        if val:
            return str(val).strip().split(".")[0]  # remove decimal if present
    return ""


class CemadenLoader(GeoLoader):
    """Creates deslizamento/inundacao layers using IBGE municipal polygons.

    Requires `mesh` kwarg: dict[ibge_code, {name, state, geom_wkt}] from IbgeMeshLoader.
    """

    def load(self, session: Any, mesh: dict | None = None, **kwargs: Any) -> LayerStats:
        if not mesh:
            return LayerStats("cemaden", 0, SOURCE, errors=["mesh dict não fornecido ou vazio"])

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
                code = _extract_ibge_code(props)

                # CEMADEN may use 6-digit codes; find matching 7-digit key in mesh
                if len(code) == 6:
                    matched = [k for k in mesh if k.startswith(code)]
                    code = matched[0] if len(matched) == 1 else ""

                if not code or code not in mesh:
                    if code:
                        all_errors.append(f"{layer_type}: ibge_code {code!r} não encontrado na malha")
                    continue

                entry = mesh[code]
                try:
                    geom = from_wkt(entry["geom_wkt"])
                    features.append(
                        {
                            "name": entry["name"],
                            "attributes": {"ibge_code": code, "state": entry["state"]},
                            "geom": geom,
                        }
                    )
                except Exception as exc:
                    all_errors.append(f"{layer_type} geom parse {code}: {exc}")

            count = bulk_insert_geodata(session, layer_type, features, SOURCE)
            session.commit()
            total_loaded += count

        return LayerStats(
            layer_type="cemaden",
            polygons_loaded=total_loaded,
            source=SOURCE,
            errors=all_errors,
        )
