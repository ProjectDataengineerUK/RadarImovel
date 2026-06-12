from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field


@dataclass
class RawProperty:
    external_code: str
    source_url: str
    raw_data: dict
    bank_code: str
    source_name: str
    extra: dict = field(default_factory=dict)


class BankConnector(ABC):
    bank_code: str
    # Onda 3: generic source attributes
    source_type: str = "bank"      # "bank" | "auctioneer" | "court"
    source_code: str = ""          # mirrors bank_code; set per subclass
    tos_compliant: bool = True     # leiloeiros start False until ToS reviewed

    @property
    def _effective_source_code(self) -> str:
        return self.source_code or self.bank_code

    @abstractmethod
    def discover_sources(self) -> list[str]:
        """Retorna lista de URLs/arquivos a coletar (ex: lista por UF)."""

    @abstractmethod
    def fetch_raw(self, source_url: str) -> bytes:
        """Baixa arquivo bruto (HTML, XLSX, PDF) e retorna bytes."""

    @abstractmethod
    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        """Converte bytes brutos em RawProperty iteráveis."""

    @abstractmethod
    def normalize(self, raw: RawProperty) -> dict:
        """Converte RawProperty para o schema padrão de Property."""


# Alias para código novo; código existente continua usando BankConnector
SourceConnector = BankConnector
