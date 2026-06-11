import json
from unittest.mock import MagicMock, patch

import pytest
import requests
from shapely.geometry import Polygon, mapping

from app.geodata.loaders.funai import FunaiLoader


def _ti_feature(name: str = "Terra Indígena Xingu", etnia: str = "Kayabi") -> dict:
    poly = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
    return {
        "type": "Feature",
        "geometry": mapping(poly),
        "properties": {
            "terrai_nom": name,
            "etnia_nome": etnia,
            "fase_ti": "Regularizada",
            "modalidade": "Reserva Indígena",
            "municipio_id": "5107800",
        },
    }


def _make_response(features: list[dict], status_code: int = 200) -> requests.Response:
    body = json.dumps({"type": "FeatureCollection", "features": features})
    req = requests.Request("GET", "https://geoserver.funai.gov.br").prepare()
    resp = requests.models.Response()
    resp.status_code = status_code
    resp._content = body.encode()
    resp.request = req
    return resp


def test_load_basic():
    session = MagicMock()
    response = _make_response([_ti_feature(), _ti_feature("TI Kayapó")])

    with patch("app.geodata.loaders.funai.requests.get", return_value=response):
        with patch("app.geodata.loaders.funai.bulk_insert_geodata", return_value=2) as mock_insert:
            stats = FunaiLoader().load(session)

    assert stats.layer_type == "TI"
    assert stats.polygons_loaded == 2
    assert len(stats.errors) == 0
    _, lt, feats, _ = mock_insert.call_args[0]
    assert lt == "TI"
    assert feats[0]["name"] == "Terra Indígena Xingu"
    assert feats[0]["attributes"]["etnia"] == "Kayabi"


def test_load_http_error():
    """FunaiLoader propagates HTTP errors; job.py is responsible for catching them."""
    session = MagicMock()
    with pytest.raises(requests.exceptions.Timeout):
        with patch(
            "app.geodata.loaders.funai.requests.get",
            side_effect=requests.exceptions.Timeout("timeout"),
        ):
            FunaiLoader().load(session)


def test_load_empty_collection():
    session = MagicMock()
    response = _make_response([])

    with patch("app.geodata.loaders.funai.requests.get", return_value=response):
        with patch("app.geodata.loaders.funai.bulk_insert_geodata", return_value=0):
            stats = FunaiLoader().load(session)

    assert stats.polygons_loaded == 0
