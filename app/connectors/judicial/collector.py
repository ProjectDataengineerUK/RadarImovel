"""JudicialConnector — coleta hastas públicas via DataJud/CNJ.

Cobre TRT-1 a TRT-24, TRF-1 a TRF-6 e principais TJs via API pública do CNJ.
A env var TRIBUNAL seleciona o tribunal; cada execução de job cobre 1 tribunal.
"""
from __future__ import annotations

import json
from collections.abc import Iterator

from app.connectors.base import BankConnector, RawProperty
from app.connectors.judicial.normalizer import JudicialNormalizer
from app.connectors.judicial.parser import JudicialParser
from app.core.logging import logger
from app.risk.sources.datajud import DataJudClient

_MAX_PAGES = 10
_PAGE_SIZE = 100


class JudicialConnector(BankConnector):
    bank_code = "judicial"
    source_code = "judicial"
    source_type = "court"
    tos_compliant = True

    def __init__(self, tribunal: str = "TRT2", days_back: int = 30) -> None:
        self._tribunal = tribunal.upper()
        self._days_back = days_back
        self._client = DataJudClient()
        self._parser = JudicialParser(tribunal=self._tribunal)
        self._normalizer = JudicialNormalizer()

    def discover_sources(self) -> list[str]:
        return [f"{self._tribunal}:{p}" for p in range(_MAX_PAGES)]

    def fetch_raw(self, source_url: str) -> bytes:
        parts = source_url.split(":")
        tribunal = parts[0]
        page = int(parts[1]) if len(parts) > 1 else 0
        hits = self._client.search_hastas_tribunal(
            tribunal,
            days_back=self._days_back,
            page=page,
            size=_PAGE_SIZE,
        )
        if not hits:
            return b""
        logger.info("judicial.fetch_ok", tribunal=tribunal, page=page, count=len(hits))
        return json.dumps(hits).encode()

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self._parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self._normalizer.normalize(raw)
