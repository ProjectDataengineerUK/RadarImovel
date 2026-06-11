"""Connector Banrisul.

Página de bens à venda Banrisul (HTML). Banco gaúcho — default state RS quando
ausente. URL e estrutura são hipóteses a validar no build.
"""
from collections.abc import Iterator

import httpx

from app.connectors.banrisul.normalizer import BanrisulNormalizer
from app.connectors.banrisul.parser import BanrisulParser
from app.connectors.base import BankConnector, RawProperty
from app.connectors.playwright_utils import fetch_with_playwright
from app.core.logging import logger

BANRISUL_LIST_URL = "https://www.banrisul.com.br/bob/site/link/bens-a-venda.html"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class BanrisulConnector(BankConnector):
    bank_code = "banrisul"

    def __init__(self, uf: str | None = None):
        self.uf = uf
        self.parser = BanrisulParser()
        self.normalizer = BanrisulNormalizer()

    def discover_sources(self) -> list[str]:
        return [BANRISUL_LIST_URL]

    def fetch_raw(self, source_url: str) -> bytes:
        # SPA page — Playwright renders the JavaScript-loaded property listings
        content = fetch_with_playwright(source_url)
        if not content:
            try:
                with httpx.Client(
                    headers=_HEADERS, timeout=30, follow_redirects=True
                ) as client:
                    resp = client.get(source_url)
                    resp.raise_for_status()
                    content = resp.content
            except Exception as exc:
                logger.error("banrisul.fetch_failed", url=source_url, error=str(exc))
                return b""

        head = content[:512].lower()
        if b"captcha" in head or b"challenge" in head:
            logger.warning("banrisul.fetch_got_challenge", url=source_url)
            return b""
        logger.info("banrisul.fetch_ok", url=source_url, size=len(content))
        return content

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self.parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
