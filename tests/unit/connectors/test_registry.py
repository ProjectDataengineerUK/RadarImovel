import pytest

from app.connectors import CONNECTOR_REGISTRY, get_connector
from app.connectors.banestes import BanestesConnector
from app.connectors.banrisul import BanrisulConnector
from app.connectors.basa import BASAConnector
from app.connectors.bb import BBConnector
from app.connectors.bnb import BNBConnector
from app.connectors.brb import BRBConnector
from app.connectors.caixa import CaixaConnector

EXPECTED = {
    "caixa": CaixaConnector,
    "bb": BBConnector,
    "brb": BRBConnector,
    "bnb": BNBConnector,
    "basa": BASAConnector,
    "banrisul": BanrisulConnector,
    "banestes": BanestesConnector,
}


def test_registry_has_seven_banks():
    assert set(CONNECTOR_REGISTRY) == set(EXPECTED)


@pytest.mark.parametrize("code,cls", list(EXPECTED.items()))
def test_get_connector_resolves(code, cls):
    connector = get_connector(code)
    assert isinstance(connector, cls)
    assert connector.bank_code == code


def test_get_connector_case_insensitive():
    assert isinstance(get_connector("  BB "), BBConnector)


def test_get_connector_unknown_raises():
    with pytest.raises(ValueError):
        get_connector("itau")


def test_get_connector_passes_kwargs():
    connector = get_connector("caixa", uf="SP")
    assert connector.uf == "SP"
