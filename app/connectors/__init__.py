from app.connectors.banestes import BanestesConnector
from app.connectors.banrisul import BanrisulConnector
from app.connectors.basa import BASAConnector
from app.connectors.base import BankConnector, RawProperty, SourceConnector
from app.connectors.bb import BBConnector
from app.connectors.bnb import BNBConnector
from app.connectors.brb import BRBConnector
from app.connectors.caixa import CaixaConnector
from app.connectors.fidalgo.collector import FidalgoConnector
from app.connectors.frazao.collector import FrazaoConnector
from app.connectors.mega.collector import MegaConnector
from app.connectors.sodre.collector import SodreConnector
from app.connectors.zuk.collector import ZukConnector

CONNECTOR_REGISTRY: dict[str, type[BankConnector]] = {
    "caixa": CaixaConnector,
    "bb": BBConnector,
    "brb": BRBConnector,
    "bnb": BNBConnector,
    "basa": BASAConnector,
    "banrisul": BanrisulConnector,
    "banestes": BanestesConnector,
}

# SOURCE_REGISTRY: bancos + leiloeiros (tos_compliant=False bloqueados por padrão no job)
SOURCE_REGISTRY: dict[str, type[SourceConnector]] = {
    **CONNECTOR_REGISTRY,
    "zuk": ZukConnector,
    "mega": MegaConnector,
    "sodre": SodreConnector,
    "fidalgo": FidalgoConnector,
    "frazao": FrazaoConnector,
}


def get_connector(bank_code: str, **kwargs) -> BankConnector:
    code = bank_code.lower().strip()
    if code not in CONNECTOR_REGISTRY:
        raise ValueError(f"Connector não registrado para banco '{code}'")
    return CONNECTOR_REGISTRY[code](**kwargs)


def get_source(source_code: str, **kwargs) -> SourceConnector:
    code = source_code.lower().strip()
    if code not in SOURCE_REGISTRY:
        raise ValueError(f"Connector não registrado para fonte '{code}'")
    return SOURCE_REGISTRY[code](**kwargs)


__all__ = [
    "BankConnector",
    "SourceConnector",
    "RawProperty",
    "CONNECTOR_REGISTRY",
    "SOURCE_REGISTRY",
    "get_connector",
    "get_source",
]
