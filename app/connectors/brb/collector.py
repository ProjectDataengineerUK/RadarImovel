"""Connector BRB.

Duas fontes: página oficial de imóveis BRB (HTML) e Feirão BRB / Resale
(possível JSON de API). URLs e formato são hipóteses a validar no build.
"""
from collections.abc import Iterator

import httpx

from app.connectors.base import BankConnector, RawProperty
from app.connectors.brb.normalizer import BRBNormalizer
from app.connectors.brb.parser import BRBParser
from app.core.logging import logger

BRB_OFICIAL_URL = "https://www.brb.com.br/a-brb/leiloes-e-vendas/imoveis-proprios"
BRB_RESALE_URL = "https://brb.resale.com.br/"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/json,application/xhtml+xml;q=0.9,*/*;q=0.8",
}


class BRBConnector(BankConnector):
    bank_code = "brb"

    def __init__(self, uf: str | None = None):
        self.uf = uf
        self.parser = BRBParser()
        self.normalizer = BRBNormalizer()

    def discover_sources(self) -> list[str]:
        return [BRB_OFICIAL_URL, BRB_RESALE_URL]

    def fetch_raw(self, source_url: str) -> bytes:
        try:
            with httpx.Client(
                headers=_HEADERS, timeout=30, follow_redirects=True
            ) as client:
                resp = client.get(source_url)
                resp.raise_for_status()
                content = resp.content
        except Exception as exc:
            logger.error("brb.fetch_failed", url=source_url, error=str(exc))
            return b""

        head = content[:512].lower()
        if b"captcha" in head:
            logger.warning("brb.fetch_got_challenge", url=source_url)
            return b""
        logger.info("brb.fetch_ok", url=source_url, size=len(content))
        return content

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self.parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
