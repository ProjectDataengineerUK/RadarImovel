"""Connector Sodré Santoro (sodresantoro.com.br) — leiloeiro tradicional SP/RJ."""
from collections.abc import Iterator

import httpx

from app.connectors.base import BankConnector, RawProperty
from app.connectors.sodre.normalizer import SodreNormalizer
from app.connectors.sodre.parser import SodreParser
from app.connectors.playwright_utils import fetch_with_playwright
from app.core.logging import logger

SODRE_IMOVEIS_URL = "https://www.sodresantoro.com.br/leiloes/imoveis"
# Nuxt 3 SPA: ?page=N returns 404 for all N>0; pagination is client-side only.
_SODRE_WAIT_SELECTOR = "a[href*='/leilao'], a[href*='/lote'], a[href*='/bem'], a[href*='/imovel']"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://www.sodresantoro.com.br/",
}


class SodreConnector(BankConnector):
    bank_code = "sodre"
    source_code = "sodre"
    source_type = "auctioneer"
    tos_compliant = False

    def __init__(self, uf: str | None = None):
        self.uf = uf
        self.parser = SodreParser()
        self.normalizer = SodreNormalizer()

    def discover_sources(self) -> list[str]:
        # Nuxt 3 SPA: all property cards are on a single URL (client-side pagination).
        return [SODRE_IMOVEIS_URL]

    def fetch_raw(self, source_url: str) -> bytes:
        # Sodre blocks plain HTTP (403); Playwright required.
        # Wait for at least one auction link to confirm the listing is hydrated.
        content = fetch_with_playwright(
            source_url,
            wait_until="networkidle",
            wait_selector=_SODRE_WAIT_SELECTOR,
        )
        if not content:
            try:
                with httpx.Client(headers=_HEADERS, timeout=30, follow_redirects=True) as client:
                    resp = client.get(source_url)
                    resp.raise_for_status()
                    content = resp.content
            except Exception as exc:
                logger.error("sodre.fetch_failed", url=source_url, error=str(exc))
                return b""
        if not content or b"captcha" in content[:512].lower():
            logger.warning("sodre.fetch_blocked", url=source_url)
            return b""
        logger.info("sodre.fetch_ok", url=source_url, size=len(content))
        return content

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self.parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
