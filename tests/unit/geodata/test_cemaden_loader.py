from unittest.mock import MagicMock, patch

from shapely.geometry import Polygon

from app.geodata.loaders.cemaden import CemadenLoader

MESH = {
    "3550308": {"name": "São Paulo", "state": "SP", "geom_wkt": Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]).wkt},
    "3300456": {"name": "Rio de Janeiro", "state": "RJ", "geom_wkt": Polygon([(2, 2), (3, 2), (3, 3), (2, 3)]).wkt},
    "1302603": {"name": "Manaus", "state": "AM", "geom_wkt": Polygon([(5, 5), (6, 5), (6, 6), (5, 6)]).wkt},
}

CEMADEN_DESLIZAMENTO = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "geometry": None, "properties": {"codibge": "3550308", "nome": "São Paulo"}},
        {"type": "Feature", "geometry": None, "properties": {"codibge": "9999999", "nome": "Município Inexistente"}},
    ],
}
CEMADEN_INUNDACAO = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "geometry": None, "properties": {"codibge": "3300456", "nome": "Rio de Janeiro"}},
    ],
}


def _mock_fetch(layer_data: dict):
    def _inner(urls):
        if "deslizamento" in urls[0]:
            return layer_data.get("deslizamento")
        return layer_data.get("inundacao")
    return _inner


def test_load_maps_ibge_codes_to_mesh_polygons():
    session = MagicMock()
    layer_data = {"deslizamento": CEMADEN_DESLIZAMENTO, "inundacao": CEMADEN_INUNDACAO}

    with patch("app.geodata.loaders.cemaden._fetch_first_available", side_effect=_mock_fetch(layer_data)):
        with patch("app.geodata.loaders.cemaden.bulk_insert_geodata", return_value=1):
            stats = CemadenLoader().load(session, mesh=MESH)

    assert stats.polygons_loaded == 2  # 1 deslizamento + 1 inundacao
    assert stats.layer_type == "cemaden"
    # Unknown ibge_code 9999999 goes to errors
    assert any("9999999" in e for e in stats.errors)


def test_load_6digit_code_resolution():
    """6-digit IBGE code should resolve to 7-digit via prefix match."""
    mesh = {
        "3550308": {"name": "São Paulo", "state": "SP", "geom_wkt": Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]).wkt}
    }
    data = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": None, "properties": {"codibge": "355030", "nome": "SP"}},
        ],
    }
    session = MagicMock()

    with patch("app.geodata.loaders.cemaden._fetch_first_available", return_value=data):
        with patch("app.geodata.loaders.cemaden.bulk_insert_geodata", return_value=1):
            stats = CemadenLoader().load(session, mesh=mesh)

    assert stats.polygons_loaded >= 1 or any("355030" in e for e in stats.errors)


def test_load_without_mesh_returns_error():
    session = MagicMock()
    stats = CemadenLoader().load(session, mesh=None)
    assert stats.polygons_loaded == 0
    assert len(stats.errors) > 0
    assert "mesh" in stats.errors[0].lower()


def test_load_all_urls_fail():
    session = MagicMock()
    with patch("app.geodata.loaders.cemaden._fetch_first_available", return_value=None):
        stats = CemadenLoader().load(session, mesh=MESH)

    assert stats.polygons_loaded == 0
    assert len(stats.errors) == 2  # one per layer_type
    assert any("deslizamento" in e for e in stats.errors)
    assert any("inundacao" in e for e in stats.errors)
