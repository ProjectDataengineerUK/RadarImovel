import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import requests

from app.geodata.loaders.ipea_violence import IpeaViolenceLoader


def _make_xlsx_response(df: pd.DataFrame) -> requests.Response:
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    req = requests.Request("GET", "https://www.ipea.gov.br").prepare()
    resp = requests.models.Response()
    resp.status_code = 200
    resp._content = buf.read()
    resp.request = req
    return resp


def test_load_extracts_homicide_rates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session = MagicMock()
    df = pd.DataFrame(
        {
            "codmun": ["3550308", "3300456", "5300108"],
            "taxaHomicidios2022": ["18.5", "25.3", "12.1"],
        }
    )
    response = _make_xlsx_response(df)

    with patch("app.geodata.loaders.ipea_violence.requests.get", return_value=response):
        stats = IpeaViolenceLoader().load(session)

    assert stats.polygons_loaded == 3
    assert len(stats.errors) == 0
    assert Path("data/atlas_violencia.csv").exists()
    csv_df = pd.read_csv("data/atlas_violencia.csv")
    assert len(csv_df) == 3
    assert set(csv_df.columns) == {"ibge_code", "year", "homicide_rate"}


def test_load_uses_latest_year_column(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session = MagicMock()
    df = pd.DataFrame(
        {
            "codmun": ["3550308"],
            "taxaHomicidios2019": ["20.0"],
            "taxaHomicidios2021": ["18.0"],
            "taxaHomicidios2022": ["15.0"],  # most recent — should be used
        }
    )
    response = _make_xlsx_response(df)

    with patch("app.geodata.loaders.ipea_violence.requests.get", return_value=response):
        stats = IpeaViolenceLoader().load(session)

    assert stats.polygons_loaded == 1
    db_rows = session.execute.call_args[0][1]
    assert db_rows[0]["homicide_rate"] == 15.0


def test_load_missing_columns_returns_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session = MagicMock()
    df = pd.DataFrame({"municipio": ["São Paulo"], "populacao": [12000000]})
    response = _make_xlsx_response(df)

    with patch("app.geodata.loaders.ipea_violence.requests.get", return_value=response):
        stats = IpeaViolenceLoader().load(session)

    assert stats.polygons_loaded == 0
    assert len(stats.errors) > 0


def test_load_http_error():
    session = MagicMock()
    with patch(
        "app.geodata.loaders.ipea_violence.requests.get",
        side_effect=requests.RequestException("server error"),
    ):
        stats = IpeaViolenceLoader().load(session)

    assert stats.polygons_loaded == 0
    assert "server error" in stats.errors[0]
