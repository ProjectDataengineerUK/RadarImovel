"""Connector Lance Certo Leilões — especializado em leilões judiciais."""
from __future__ import annotations

from collections.abc import Iterator

import httpx

from app.connectors.base import BankConnector, RawProperty
from app.connectors.lance_certo.normalizer import LanceCertoNormalizer
from app.connectors.lance_certo.parser import LanceCertoParser
from app.connectors.playwright_utils import fetch_with_playwright
from app.core.logging import logger

_BASE_URL = "https://www.lancecerto.com.br"
_CATEGORIES = ["imoveis", "imovel-residencial", "imovel-comercial"]
_MAX_PAGES = 20

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml,*/*",
}


class LanceCertoConnector(BankConnector):
    bank_code = "lance_certo"
    source_code = "lance_certo"
    source_type = "auctioneer"
    tos_compliant = False

    def __init__(self, category: str = "imoveis") -> None:
        self._category = category
        self._parser = LanceCertoParser()
        self._normalizer = LanceCertoNormalizer()

    def discover_sources(self) -> list[str]:
        return [
            f"{_BASE_URL}/leiloes/{cat}?page={p}"
            for cat in _CATEGORIES
            for p in range(1, _MAX_PAGES + 1)
        ]

    def fetch_raw(self, source_url: str) -> bytes:
        try:
            with httpx.Client(headers=_HEADERS, timeout=20, follow_redirects=True) as client:
                resp = client.get(source_url)
                if resp.status_code == 403:
                    logger.info("lance_certo.403_fallback_playwright", url=source_url)
                    return fetch_with_playwright(source_url) or b""
                resp.raise_for_status()
                return resp.content
        except Exception as exc:
            logger.warning("lance_certo.fetch_error", url=source_url, error=str(exc))
            return b""

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self._parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self._normalizer.normalize(raw)
