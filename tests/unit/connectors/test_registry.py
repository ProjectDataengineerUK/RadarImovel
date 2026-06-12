import pytest

from app.connectors import CONNECTOR_REGISTRY, SOURCE_REGISTRY, get_connector, get_source
from app.connectors.banestes import BanestesConnector
from app.connectors.banrisul import BanrisulConnector
from app.connectors.basa import BASAConnector
from app.connectors.bb import BBConnector
from app.connectors.bnb import BNBConnector
from app.connectors.brb import BRBConnector
from app.connectors.caixa import CaixaConnector
from app.connectors.fidalgo.collector import FidalgoConnector
from app.connectors.frazao.collector import FrazaoConnector
from app.connectors.mega.collector import MegaConnector
from app.connectors.sodre.collector import SodreConnector
from app.connectors.zuk.collector import ZukConnector

EXPECTED_BANKS = {
    "caixa": CaixaConnector,
    "bb": BBConnector,
    "brb": BRBConnector,
    "bnb": BNBConnector,
    "basa": BASAConnector,
    "banrisul": BanrisulConnector,
    "banestes": BanestesConnector,
}

EXPECTED_SOURCES = {
    **EXPECTED_BANKS,
    "zuk": ZukConnector,
    "mega": MegaConnector,
    "sodre": SodreConnector,
    "fidalgo": FidalgoConnector,
    "frazao": FrazaoConnector,
}


def test_registry_has_seven_banks():
    assert set(CONNECTOR_REGISTRY) == set(EXPECTED_BANKS)


def test_source_registry_has_twelve_sources():
    assert set(SOURCE_REGISTRY) == set(EXPECTED_SOURCES)


@pytest.mark.parametrize("code,cls", list(EXPECTED_BANKS.items()))
def test_get_connector_resolves(code, cls):
    connector = get_connector(code)
    assert isinstance(connector, cls)
    assert connector.bank_code == code


@pytest.mark.parametrize("code,cls", [("zuk", ZukConnector), ("mega", MegaConnector), ("fidalgo", FidalgoConnector)])
def test_get_source_resolves_leiloeiros(code, cls):
    connector = get_source(code)
    assert isinstance(connector, cls)
    assert connector.source_type == "auctioneer"


def test_get_connector_case_insensitive():
    assert isinstance(get_connector("  BB "), BBConnector)


def test_get_connector_unknown_raises():
    with pytest.raises(ValueError):
        get_connector("itau")


def test_get_source_unknown_raises():
    with pytest.raises(ValueError):
        get_source("itau")


def test_get_connector_passes_kwargs():
    connector = get_connector("caixa", uf="SP")
    assert connector.uf == "SP"
