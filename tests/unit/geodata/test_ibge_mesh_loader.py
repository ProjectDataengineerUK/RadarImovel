import io
import os
import tempfile
import zipfile
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from app.geodata.loaders.ibge_mesh import IbgeMeshLoader


def _make_zip_response(ibge_codes: list[tuple]) -> bytes:
    """Create a minimal ZIP with a shapefile GeoDataFrame for testing."""
    # ibge_codes: list of (CD_MUN, NM_MUN, SIGLA_UF, polygon)
    features = []
    for code, name, state, poly in ibge_codes:
        features.append(
            {
                "CD_MUN": code,
                "NM_MUN": name,
                "SIGLA_UF": state,
                "geometry": poly,
            }
        )
    gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")

    with tempfile.TemporaryDirectory() as tmpdir:
        shp_path = os.path.join(tmpdir, "BR_Municipios_2022.shp")
        gdf.to_file(shp_path, driver="ESRI Shapefile")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for fname in os.listdir(tmpdir):
                zf.write(os.path.join(tmpdir, fname), fname)
        return buf.getvalue()


def _make_http_response(content: bytes, status_code: int = 200):
    import requests

    req = requests.Request("GET", "https://geoftp.ibge.gov.br").prepare()
    resp = requests.models.Response()
    resp.status_code = status_code
    resp._content = content
    resp.request = req
    return resp


@pytest.fixture
def zip_bytes():
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    return _make_zip_response(
        [
            ("3550308", "São Paulo", "SP", poly),
            ("3300456", "Rio de Janeiro", "RJ", poly),
            ("5300108", "Brasília", "DF", poly),
        ]
    )


def test_load_mesh_populates_ibge_codes(zip_bytes):
    session = MagicMock()
    response = _make_http_response(zip_bytes)

    with patch("app.geodata.loaders.ibge_mesh.requests.get", return_value=response):
        with patch("app.geodata.loaders.ibge_mesh.upsert_municipality_stats", return_value=3) as mock_upsert:
            result = IbgeMeshLoader().load_mesh(session)

    assert result.municipalities_loaded == 3
    assert len(result.errors) == 0
    assert "3550308" in result.mesh
    assert result.mesh["3550308"]["name"] == "São Paulo"
    assert result.mesh["3550308"]["state"] == "SP"
    assert "geom_wkt" in result.mesh["3550308"]
    mock_upsert.assert_called_once()
    rows = mock_upsert.call_args[0][1]
    assert len(rows) == 3
    assert all(r["ibge_code"] in ("3550308", "3300456", "5300108") for r in rows)


def test_load_mesh_skips_invalid_codes(zip_bytes):
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    bad_zip = _make_zip_response(
        [
            ("123", "Código Curto", "XX", poly),   # invalid 3-digit code
            ("3550308", "São Paulo", "SP", poly),
        ]
    )
    session = MagicMock()
    response = _make_http_response(bad_zip)

    with patch("app.geodata.loaders.ibge_mesh.requests.get", return_value=response):
        with patch("app.geodata.loaders.ibge_mesh.upsert_municipality_stats", return_value=1):
            result = IbgeMeshLoader().load_mesh(session)

    assert "3550308" in result.mesh
    assert "123" not in result.mesh
    assert any("123" in e for e in result.errors)
