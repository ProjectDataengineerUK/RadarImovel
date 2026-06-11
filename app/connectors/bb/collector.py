"""Connector Banco do Brasil (bb).

Portal de venda de imóveis BB. URL e estrutura HTML são hipóteses a validar no
build — isoladas nas constantes abaixo. Coleta nacional (sem split por UF).
"""
from collections.abc import Iterator

import httpx

from app.connectors.base import BankConnector, RawProperty
from app.connectors.bb.normalizer import BBNormalizer
from app.connectors.bb.parser import BBParser
from app.connectors.playwright_utils import fetch_with_playwright
from app.core.logging import logger

BB_LIST_URLS = [
    "https://www.bb.com.br/site/compras-contratacao-e-venda-de-imoveis/venda-de-imoveis/",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_HTML_PREFIXES = (b"<html", b"<!doc", b"<head", b"<!DOC", b"<HTML", b"<HEAD")


class BBConnector(BankConnector):
    bank_code = "bb"

    def __init__(self, uf: str | None = None):
        self.uf = uf
        self.parser = BBParser()
        self.normalizer = BBNormalizer()

    def discover_sources(self) -> list[str]:
        return list(BB_LIST_URLS)

    def fetch_raw(self, source_url: str) -> bytes:
        try:
            with httpx.Client(
                headers=_HEADERS, timeout=30, follow_redirects=True
            ) as client:
                resp = client.get(source_url)
                resp.raise_for_status()
                content = resp.content
        except Exception as exc:
            logger.error("bb.fetch_failed", url=source_url, error=str(exc))
            return self._try_playwright(source_url)

        if self._looks_like_challenge(content):
            logger.warning("bb.fetch_got_challenge", url=source_url, size=len(content))
            return self._try_playwright(source_url)

        logger.info("bb.fetch_ok", url=source_url, size=len(content))
        return content

    def _looks_like_challenge(self, content: bytes) -> bool:
        head = content[:512].lower()
        if not content:
            return True
        if b"captcha" in head or b"challenge" in head:
            return True
        return False

    def _try_playwright(self, url: str) -> bytes:
        return fetch_with_playwright(url)

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self.parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
