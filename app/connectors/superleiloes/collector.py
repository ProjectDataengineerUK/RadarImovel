"""Connector Super Leilões — plataforma de leilões judiciais e extrajudiciais."""
from __future__ import annotations

from collections.abc import Iterator

import httpx

from app.connectors.base import BankConnector, RawProperty
from app.connectors.playwright_utils import fetch_with_playwright
from app.connectors.superleiloes.normalizer import SuperleiloesNormalizer
from app.connectors.superleiloes.parser import SuperleiloesParser
from app.core.logging import logger

_BASE_URL = "https://www.superleiloes.com.br"
_MAX_PAGES = 20
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "application/json, text/html, */*",
}


class SuperleiloesConnector(BankConnector):
    bank_code = "superleiloes"
    source_code = "superleiloes"
    source_type = "auctioneer"
    tos_compliant = False

    def __init__(self) -> None:
        self._parser = SuperleiloesParser()
        self._normalizer = SuperleiloesNormalizer()

    def discover_sources(self) -> list[str]:
        return [
            f"{_BASE_URL}/lotes/imoveis?pagina={p}&ordenar=maior-desconto"
            for p in range(1, _MAX_PAGES + 1)
        ]

    def fetch_raw(self, source_url: str) -> bytes:
        json_url = source_url.replace("/lotes/", "/api/lotes/") if "/lotes/" in source_url else source_url
        try:
            with httpx.Client(headers=_HEADERS, timeout=20, follow_redirects=True) as client:
                resp = client.get(json_url)
                if resp.status_code == 200 and "application/json" in resp.headers.get("content-type", ""):
                    return resp.content
                resp2 = client.get(source_url)
                if resp2.status_code == 403:
                    logger.info("superleiloes.403_fallback_playwright", url=source_url)
                    return fetch_with_playwright(source_url) or b""
                resp2.raise_for_status()
                return resp2.content
        except Exception as exc:
            logger.warning("superleiloes.fetch_error", url=source_url, error=str(exc))
            return b""

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self._parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self._normalizer.normalize(raw)
