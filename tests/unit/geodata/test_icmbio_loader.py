import json
from unittest.mock import MagicMock, patch

import requests
from shapely.geometry import Polygon, mapping

from app.geodata.loaders.icmbio import IcmbioLoader


def _polygon_feature(name: str = "APA Botucatu") -> dict:
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    return {
        "type": "Feature",
        "geometry": mapping(poly),
        "properties": {"nome_uc": name, "categoria_uc": "APA", "area_ha": "10000"},
    }


def _make_response(features: list[dict], status_code: int = 200) -> requests.Response:
    body = json.dumps({"type": "FeatureCollection", "features": features})
    req = requests.Request("GET", "https://geo.icmbio.gov.br/geoserver/wfs").prepare()
    resp = requests.models.Response()
    resp.status_code = status_code
    resp._content = body.encode()
    resp.request = req
    return resp


def test_load_single_page():
    session = MagicMock()
    features = [_polygon_feature(f"UC {i}") for i in range(3)]
    response = _make_response(features)

    with patch("app.geodata.loaders.icmbio.requests.get", return_value=response):
        with patch("app.geodata.loaders.icmbio.bulk_insert_geodata", return_value=3) as mock_insert:
            stats = IcmbioLoader().load(session)

    assert stats.polygons_loaded == 3
    assert stats.layer_type == "UC"
    assert len(stats.errors) == 0
    mock_insert.assert_called_once()
    _, lt, feats, _ = mock_insert.call_args[0]
    assert lt == "UC"
    assert len(feats) == 3


def test_load_extracts_nome_uc():
    session = MagicMock()
    response = _make_response([_polygon_feature("Parque Nacional da Serra")])

    with patch("app.geodata.loaders.icmbio.requests.get", return_value=response):
        with patch("app.geodata.loaders.icmbio.bulk_insert_geodata", return_value=1) as mock_insert:
            IcmbioLoader().load(session)

    feats = mock_insert.call_args[0][2]
    assert feats[0]["name"] == "Parque Nacional da Serra"


def test_load_empty_page_stops_pagination():
    session = MagicMock()
    # First call returns 0 features → stop immediately
    response = _make_response([])

    with patch("app.geodata.loaders.icmbio.requests.get", return_value=response):
        with patch("app.geodata.loaders.icmbio.bulk_insert_geodata", return_value=0) as mock_insert:
            stats = IcmbioLoader().load(session)

    assert stats.polygons_loaded == 0
    mock_insert.assert_called_once_with(session, "UC", [], "ICMBio WFS 2.0.0 — CADASTRO_UC_WGS84")


def test_load_http_error_captured():
    session = MagicMock()
    with patch(
        "app.geodata.loaders.icmbio.requests.get",
        side_effect=requests.RequestException("connection timeout"),
    ):
        with patch("app.geodata.loaders.icmbio.bulk_insert_geodata", return_value=0):
            stats = IcmbioLoader().load(session)

    assert len(stats.errors) > 0
    assert "connection timeout" in stats.errors[0]


def test_load_pagination_stops_on_partial_page():
    """When page returns fewer than PAGE_SIZE features, pagination should stop."""
    session = MagicMock()
    # Return 2 features (< PAGE_SIZE=500) → only one HTTP call
    features = [_polygon_feature(f"UC {i}") for i in range(2)]
    response = _make_response(features)

    call_count = 0

    def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return response

    with patch("app.geodata.loaders.icmbio.requests.get", side_effect=mock_get):
        with patch("app.geodata.loaders.icmbio.bulk_insert_geodata", return_value=2):
            IcmbioLoader().load(session)

    assert call_count == 1
