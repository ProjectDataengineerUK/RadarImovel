"""Connector BRB — Feirão BRB powered by Resale (feiraobrb.com.br).

A página /busca é uma React SPA que carrega imóveis via API AWS privada.
fetch_raw usa Playwright para renderizar o JavaScript e retornar o DOM completo.
"""
from collections.abc import Iterator

from app.connectors.base import BankConnector, RawProperty
from app.connectors.brb.normalizer import BRBNormalizer
from app.connectors.brb.parser import BRBParser
from app.connectors.playwright_utils import fetch_with_playwright
from app.core.logging import logger

BRB_BUSCA_URL = "https://feiraobrb.com.br/busca"


class BRBConnector(BankConnector):
    bank_code = "brb"

    def __init__(self, uf: str | None = None):
        self.uf = uf
        self.parser = BRBParser()
        self.normalizer = BRBNormalizer()

    def discover_sources(self) -> list[str]:
        return [BRB_BUSCA_URL]

    def fetch_raw(self, source_url: str) -> bytes:
        # SPA: Playwright espera os cards PropertyCard_card renderizarem
        content = fetch_with_playwright(
            source_url,
            wait_selector="[class*='PropertyCard_card']",
            timeout_ms=45_000,
        )
        if not content:
            logger.warning("brb.fetch_empty", url=source_url)
        else:
            logger.info("brb.fetch_ok", url=source_url, size=len(content))
        return content

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self.parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
