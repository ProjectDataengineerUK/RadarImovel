"""Connector Frazão Leilões (frazaoleiloes.com.br) — leiloeiro multi-estado.

Estrutura: /lotes/busca/p/{page}?categorias=Imovel retorna lot cards .item-bid
carregados via JavaScript. Playwright é necessário; wait_selector garante que
os lotes estejam no DOM antes de capturar o HTML.
"""
from collections.abc import Iterator

import httpx

from app.connectors.base import BankConnector, RawProperty
from app.connectors.frazao.normalizer import FrazaoNormalizer
from app.connectors.frazao.parser import FrazaoParser
from app.connectors.playwright_utils import fetch_with_playwright
from app.core.logging import logger

FRAZAO_SEARCH_URL = (
    "https://www.frazaoleiloes.com.br/lotes/busca/p/{page}?categorias=Imovel"
)
FRAZAO_MAX_PAGES = 15

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


class FrazaoConnector(BankConnector):
    bank_code = "frazao"
    source_code = "frazao"
    source_type = "auctioneer"
    tos_compliant = False

    def __init__(self, uf: str | None = None):
        self.uf = uf
        self.parser = FrazaoParser()
        self.normalizer = FrazaoNormalizer()

    def discover_sources(self) -> list[str]:
        return [FRAZAO_SEARCH_URL.format(page=p) for p in range(1, FRAZAO_MAX_PAGES + 1)]

    def fetch_raw(self, source_url: str) -> bytes:
        # Frazao uses client-side rendering. Container is #content_list_lote;
        # networkidle (default) waits for JS to populate it.
        content = fetch_with_playwright(source_url)
        if not content:
            try:
                with httpx.Client(headers=_HEADERS, timeout=30, follow_redirects=True) as client:
                    resp = client.get(source_url)
                    resp.raise_for_status()
                    content = resp.content
            except Exception as exc:
                logger.error("frazao.fetch_failed", url=source_url, error=str(exc))
                return b""
        if not content or b"captcha" in content[:512].lower():
            return b""
        logger.info("frazao.fetch_ok", url=source_url, size=len(content))
        return content

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self.parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
