"""Connector Banco do Brasil (bb).

Portal oficial: seuimovelbb.com.br — página inicial é SSR com cards div.card.carta.
Não requer Playwright: httpx lê o HTML completo.
"""
import re
from collections.abc import Iterator

import httpx

from app.connectors.base import BankConnector, RawProperty
from app.connectors.bb.normalizer import BBNormalizer
from app.connectors.bb.parser import BBParser
from app.core.logging import logger

BB_HOME_URL = "https://seuimovelbb.com.br/"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_CHALLENGE_SIGNALS = (b"captcha", b"challenge", b"cloudflare")


class BBConnector(BankConnector):
    bank_code = "bb"

    def __init__(self, uf: str | None = None):
        self.uf = uf
        self.parser = BBParser()
        self.normalizer = BBNormalizer()

    def discover_sources(self) -> list[str]:
        return [BB_HOME_URL]

    def fetch_raw(self, source_url: str) -> bytes:
        try:
            with httpx.Client(headers=_HEADERS, timeout=30, follow_redirects=True) as client:
                resp = client.get(source_url)
                resp.raise_for_status()
                content = resp.content
        except Exception as exc:
            logger.error("bb.fetch_failed", url=source_url, error=str(exc))
            return b""

        head = content[:512].lower()
        if any(sig in head for sig in _CHALLENGE_SIGNALS):
            logger.warning("bb.fetch_challenge", url=source_url)
            return b""

        logger.info("bb.fetch_ok", url=source_url, size=len(content))
        return content

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self.parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
