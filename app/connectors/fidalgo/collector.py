"""Connector Fidalgo Leilões (fidalgoleiloes.com.br) — leiloeiro SP."""
from collections.abc import Iterator

import httpx

from app.connectors.base import BankConnector, RawProperty
from app.connectors.fidalgo.normalizer import FidalgoNormalizer
from app.connectors.fidalgo.parser import FidalgoParser
from app.connectors.playwright_utils import fetch_with_playwright
from app.core.logging import logger

FIDALGO_SEARCH_URL = "https://www.fidalgoleiloes.com.br/imoveis?pagina={page}"
FIDALGO_MAX_PAGES = 10

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


class FidalgoConnector(BankConnector):
    bank_code = "fidalgo"
    source_code = "fidalgo"
    source_type = "auctioneer"
    tos_compliant = False

    def __init__(self, uf: str | None = None):
        self.uf = uf
        self.parser = FidalgoParser()
        self.normalizer = FidalgoNormalizer()

    def discover_sources(self) -> list[str]:
        return [FIDALGO_SEARCH_URL.format(page=p) for p in range(1, FIDALGO_MAX_PAGES + 1)]

    def fetch_raw(self, source_url: str) -> bytes:
        content = fetch_with_playwright(source_url)
        if not content:
            try:
                with httpx.Client(headers=_HEADERS, timeout=30, follow_redirects=True) as client:
                    resp = client.get(source_url)
                    resp.raise_for_status()
                    content = resp.content
            except Exception as exc:
                logger.error("fidalgo.fetch_failed", url=source_url, error=str(exc))
                return b""
        if not content or b"captcha" in content[:512].lower():
            return b""
        return content

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self.parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
