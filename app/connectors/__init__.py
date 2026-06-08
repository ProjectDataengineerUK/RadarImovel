from app.connectors.banestes import BanestesConnector
from app.connectors.banrisul import BanrisulConnector
from app.connectors.basa import BASAConnector
from app.connectors.base import BankConnector, RawProperty
from app.connectors.bb import BBConnector
from app.connectors.bnb import BNBConnector
from app.connectors.brb import BRBConnector
from app.connectors.caixa import CaixaConnector

CONNECTOR_REGISTRY: dict[str, type[BankConnector]] = {
    "caixa": CaixaConnector,
    "bb": BBConnector,
    "brb": BRBConnector,
    "bnb": BNBConnector,
    "basa": BASAConnector,
    "banrisul": BanrisulConnector,
    "banestes": BanestesConnector,
}


def get_connector(bank_code: str, **kwargs) -> BankConnector:
    code = bank_code.lower().strip()
    if code not in CONNECTOR_REGISTRY:
        raise ValueError(f"Connector não registrado para banco '{code}'")
    return CONNECTOR_REGISTRY[code](**kwargs)


__all__ = [
    "BankConnector",
    "RawProperty",
    "CONNECTOR_REGISTRY",
    "get_connector",
]
