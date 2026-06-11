import json
from unittest.mock import MagicMock, patch

import requests

from app.geodata.loaders.ibge_sidra import IbgeSidraLoader, _parse_sidra


def _sidra_response(series_data: list[dict]) -> dict:
    """Build a SIDRA API v3 response structure."""
    return [
        {
            "resultados": [
                {
                    "series": [
                        {
                            "localidade": {"id": code, "nome": f"Município {code}"},
                            "serie": {"2022": str(value)},
                        }
                        for code, value in series_data
                    ]
                }
            ]
        }
    ]


def _make_response(data: list[dict]) -> requests.Response:
    req = requests.Request("GET", "https://servicodados.ibge.gov.br").prepare()
    resp = requests.models.Response()
    resp.status_code = 200
    resp._content = json.dumps(data).encode()
    resp.request = req
    return resp


def test_parse_sidra_basic():
    data = _sidra_response([("3550308", 12325000), ("3300456", 6748000)])
    result = _parse_sidra(data)
    assert result["3550308"] == 12325000.0
    assert result["3300456"] == 6748000.0


def test_parse_sidra_handles_ellipsis():
    data = _sidra_response([("3550308", "...")])
    result = _parse_sidra(data)
    assert result["3550308"] is None


def test_load_populates_rows():
    session = MagicMock()
    pop_data = _sidra_response([("3550308", 12325000), ("5300108", 3015268)])
    inc_data = _sidra_response([("3550308", 3200.0)])

    responses = [_make_response(pop_data), _make_response(inc_data)]

    with patch("app.geodata.loaders.ibge_sidra.requests.get", side_effect=responses):
        stats = IbgeSidraLoader().load(session)

    assert stats.polygons_loaded >= 2
    assert len(stats.errors) == 0
    session.execute.assert_called_once()
    session.commit.assert_called_once()


def test_load_population_failure_still_processes_income():
    session = MagicMock()
    inc_data = _sidra_response([("3550308", 3200.0)])
    inc_resp = _make_response(inc_data)

    with patch(
        "app.geodata.loaders.ibge_sidra.requests.get",
        side_effect=[requests.RequestException("network error"), inc_resp],
    ):
        stats = IbgeSidraLoader().load(session)

    assert "SIDRA população" in stats.errors[0]
    assert stats.polygons_loaded >= 1  # income still processed
