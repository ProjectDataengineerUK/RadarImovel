"""Connector Banco do Brasil (bb).

Portal de venda de imóveis BB. URL e estrutura HTML são hipóteses a validar no
build — isoladas nas constantes abaixo. Coleta nacional (sem split por UF).
"""
import os
from collections.abc import Iterator

import httpx

from app.connectors.base import BankConnector, RawProperty
from app.connectors.bb.normalizer import BBNormalizer
from app.connectors.bb.parser import BBParser
from app.core.logging import logger

BB_LIST_URLS = [
    "https://www21.bb.com.br/portalbb/imoveis/buscaImoveis.bb",
    "https://www47.bb.com.br/portalbb/tabelaVendaImoveis/vendaImoveis,8200,2,0.bbx",
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
        if os.environ.get("DISABLE_PLAYWRIGHT", "").lower() == "true":
            return b""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("bb.playwright_not_installed", url=url)
            return b""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                page = browser.new_context(
                    user_agent=_HEADERS["User-Agent"], locale="pt-BR"
                ).new_page()
                page.goto(url, wait_until="networkidle", timeout=30_000)
                content = page.content().encode("utf-8")
                browser.close()
                logger.info("bb.playwright_ok", url=url, size=len(content))
                return content
        except Exception as exc:
            logger.error("bb.playwright_failed", url=url, error=str(exc))
            return b""

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self.parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
