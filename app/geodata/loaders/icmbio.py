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
    """Loads federal Conservation Units (includes APAs) from ICMBio WFS with pagination."""

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
                    features.append(
                        {
                            "name": (props.get("nome_uc") or "")[:200],
                            "attributes": {
                                "categoria": props.get("categoria_uc"),
                                "grupo": props.get("grupo"),
                                "ato_legal": props.get("ato_legal_us"),
                                "area_ha": props.get("area_ha"),
                            },
                            "geom": geom,
                        }
                    )
                except Exception as exc:
                    errors.append(str(exc))

            start += len(page_features)
            if len(page_features) < PAGE_SIZE:
                break
            time.sleep(0.5)

        count = bulk_insert_geodata(session, "UC", features, SOURCE)
        session.commit()
        return LayerStats(layer_type="UC", polygons_loaded=count, source=SOURCE, errors=errors)

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
