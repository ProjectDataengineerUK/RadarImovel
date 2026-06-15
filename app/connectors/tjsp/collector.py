"""Connector TJSP via DataJud — coleta hastas públicas de imóveis do TJSP."""
from __future__ import annotations

import json
from collections.abc import Iterator

from app.connectors.base import BankConnector, RawProperty
from app.connectors.tjsp.normalizer import TJSPNormalizer
from app.connectors.tjsp.parser import TJSPParser
from app.core.logging import logger
from app.risk.sources.datajud import DataJudClient

_TRIBUNAL = "TJSP"
_MAX_PAGES = 10


class TJSPConnector(BankConnector):
    bank_code = "judicial_tjsp"
    source_code = "tjsp"
    source_type = "court"
    tos_compliant = True

    def __init__(self, days_back: int = 30) -> None:
        self._days_back = days_back
        self._client = DataJudClient()
        self._parser = TJSPParser(tribunal=_TRIBUNAL)
        self._normalizer = TJSPNormalizer()

    def discover_sources(self) -> list[str]:
        return [f"TJSP:{page}" for page in range(_MAX_PAGES)]

    def fetch_raw(self, source_url: str) -> bytes:
        try:
            page = int(source_url.split(":")[-1])
        except (ValueError, IndexError):
            page = 0
        try:
            results = self._client.search_hastas_tribunal(
                tribunal=_TRIBUNAL,
                days_back=self._days_back,
                page=page,
                size=50,
            )
            return json.dumps(results).encode()
        except Exception as exc:
            logger.warning("tjsp.fetch_raw_error", page=page, error=str(exc))
            return b"[]"

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self._parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self._normalizer.normalize(raw)
