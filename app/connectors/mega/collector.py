"""Connector Mega Leilões (megaleiloes.com.br) — leiloeiro nacional."""
from collections.abc import Iterator

import httpx

from app.connectors.base import BankConnector, RawProperty
from app.connectors.mega.normalizer import MegaNormalizer
from app.connectors.mega.parser import MegaParser
from app.connectors.playwright_utils import fetch_with_playwright
from app.core.logging import logger

MEGA_SEARCH_URL = "https://www.megaleiloes.com.br/imoveis?pagina={page}"
MEGA_MAX_PAGES = 30

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


class MegaConnector(BankConnector):
    bank_code = "mega"
    source_code = "mega"
    source_type = "auctioneer"
    tos_compliant = False

    def __init__(self, uf: str | None = None):
        self.uf = uf
        self.parser = MegaParser()
        self.normalizer = MegaNormalizer()

    def discover_sources(self) -> list[str]:
        pages = [MEGA_SEARCH_URL.format(page=p) for p in range(1, MEGA_MAX_PAGES + 1)]
        if self.uf:
            return [f"{u}&estado={self.uf.upper()}" for u in pages]
        return pages

    def fetch_raw(self, source_url: str) -> bytes:
        content = fetch_with_playwright(source_url)
        if not content:
            try:
                with httpx.Client(headers=_HEADERS, timeout=30, follow_redirects=True) as client:
                    resp = client.get(source_url)
                    resp.raise_for_status()
                    content = resp.content
            except Exception as exc:
                logger.error("mega.fetch_failed", url=source_url, error=str(exc))
                return b""
        if not content or b"captcha" in content[:512].lower():
            logger.warning("mega.fetch_blocked", url=source_url)
            return b""
        logger.info("mega.fetch_ok", url=source_url, size=len(content))
        return content

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self.parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
