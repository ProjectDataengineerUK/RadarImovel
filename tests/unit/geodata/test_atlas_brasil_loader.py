import io
from unittest.mock import MagicMock, patch

import pandas as pd
import requests

from app.geodata.loaders.atlas_brasil import AtlasBrasilLoader


def _make_xls_response(df: pd.DataFrame) -> requests.Response:
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    req = requests.Request("GET", "http://www.atlasbrasil.org.br").prepare()
    resp = requests.models.Response()
    resp.status_code = 200
    resp._content = buf.read()
    resp.request = req
    return resp


def _atlas_df(data: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(data)


def test_load_standard_columns():
    session = MagicMock()
    df = _atlas_df(
        [
            {"Codmun7": "3550308", "IDHM": "0.805"},
            {"Codmun7": "3300456", "IDHM": "0.799"},
            {"Codmun7": "5300108", "IDHM": "0.824"},
        ]
    )
    response = _make_xls_response(df)

    with patch("app.geodata.loaders.atlas_brasil.requests.get", return_value=response):
        stats = AtlasBrasilLoader().load(session)

    assert stats.polygons_loaded == 3
    assert len(stats.errors) == 0
    session.execute.assert_called_once()
    rows = session.execute.call_args[0][1]
    brasilia = next(r for r in rows if r["ibge_code"] == "5300108")
    assert brasilia["idh"] == 0.824


def test_load_idh_out_of_range_excluded():
    session = MagicMock()
    df = _atlas_df(
        [
            {"Codmun7": "3550308", "IDHM": "0.805"},
            {"Codmun7": "1234567", "IDHM": "1.500"},  # invalid > 1.0
            {"Codmun7": "9876543", "IDHM": "-0.1"},   # invalid < 0.0
        ]
    )
    response = _make_xls_response(df)

    with patch("app.geodata.loaders.atlas_brasil.requests.get", return_value=response):
        stats = AtlasBrasilLoader().load(session)

    assert stats.polygons_loaded == 1
    rows = session.execute.call_args[0][1]
    assert all(0.0 <= r["idh"] <= 1.0 for r in rows)


def test_load_missing_columns_returns_error():
    session = MagicMock()
    df = pd.DataFrame({"municipio": ["São Paulo"], "valor": [100]})
    response = _make_xls_response(df)

    with patch("app.geodata.loaders.atlas_brasil.requests.get", return_value=response):
        stats = AtlasBrasilLoader().load(session)

    assert stats.polygons_loaded == 0
    assert len(stats.errors) > 0
    assert "Colunas" in stats.errors[0]


def test_load_http_error():
    session = MagicMock()
    with patch(
        "app.geodata.loaders.atlas_brasil.requests.get",
        side_effect=requests.RequestException("404 Not Found"),
    ):
        stats = AtlasBrasilLoader().load(session)

    assert stats.polygons_loaded == 0
    assert "404" in stats.errors[0]
