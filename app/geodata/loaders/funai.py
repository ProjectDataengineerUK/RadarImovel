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
    """Loads Indigenous Lands (Terras Indígenas) with portaria from FUNAI WFS."""

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
                features.append(
                    {
                        "name": (props.get("terrai_nom") or "")[:200],
                        "attributes": {
                            "etnia": props.get("etnia_nome"),
                            "fase": props.get("fase_ti"),
                            "modalidade": props.get("modalidade"),
                            "municipio_id": props.get("municipio_id"),
                        },
                        "geom": geom,
                    }
                )
            except Exception as exc:
                errors.append(str(exc))

        count = bulk_insert_geodata(session, "TI", features, SOURCE)
        session.commit()
        return LayerStats(layer_type="TI", polygons_loaded=count, source=SOURCE, errors=errors)
