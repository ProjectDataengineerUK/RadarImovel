from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator


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
