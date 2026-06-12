"""Connector Portal Zuk (portalzuk.com.br) — leiloeiro multi-banco.

ToS review pendente: tos_compliant=False.
Coleta: listagem paginada de imóveis em leilão e venda direta.
"""
from collections.abc import Iterator

import httpx

from app.connectors.base import BankConnector, RawProperty
from app.connectors.zuk.normalizer import ZukNormalizer
from app.connectors.zuk.parser import ZukParser
from app.connectors.playwright_utils import fetch_with_playwright
from app.core.logging import logger

ZUK_BASE_URL = "https://www.portalzuk.com.br/imoveis"
ZUK_SEARCH_URL = "https://www.portalzuk.com.br/imoveis?tipo=todos&pagina={page}"
ZUK_MAX_PAGES = 20

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://www.portalzuk.com.br/",
}


class ZukConnector(BankConnector):
    bank_code = "zuk"
    source_code = "zuk"
    source_type = "auctioneer"
    tos_compliant = False  # pendente validação jurídica do ToS

    def __init__(self, uf: str | None = None):
        self.uf = uf
        self.parser = ZukParser()
        self.normalizer = ZukNormalizer()

    def discover_sources(self) -> list[str]:
        pages = [ZUK_SEARCH_URL.format(page=p) for p in range(1, ZUK_MAX_PAGES + 1)]
        if self.uf:
            # UF filtering via query param when available
            return [f"{u}&uf={self.uf.upper()}" for u in pages]
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
                logger.error("zuk.fetch_failed", url=source_url, error=str(exc))
                return b""

        if not content or b"captcha" in content[:512].lower():
            logger.warning("zuk.fetch_blocked", url=source_url)
            return b""

        logger.info("zuk.fetch_ok", url=source_url, size=len(content))
        return content

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self.parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
