import time
import tempfile
from pathlib import Path
from typing import Iterator

import httpx

from app.connectors.base import BankConnector, RawProperty
from app.connectors.caixa.parser import CaixaParser
from app.connectors.caixa.normalizer import CaixaNormalizer
from app.core.config import get_settings
from app.core.logging import logger

CAIXA_UFS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
    "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
    "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]

CAIXA_LIST_URL = "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{uf}.csv"
CAIXA_HOME_URL = "https://venda-imoveis.caixa.gov.br/"

# Injected in every new Playwright page to hide automation fingerprints
_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en-US']});
window.chrome = {runtime: {}};
"""

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class CaixaConnector(BankConnector):
    bank_code = "caixa"

    def __init__(self, uf: str | None = None):
        self.settings = get_settings()
        self.uf = uf
        self.parser = CaixaParser()
        self.normalizer = CaixaNormalizer()

    def discover_sources(self) -> list[str]:
        ufs = [self.uf] if self.uf else CAIXA_UFS
        return [CAIXA_LIST_URL.format(uf=uf) for uf in ufs]

    def fetch_raw(self, source_url: str) -> bytes:
        raw = self._try_playwright(source_url)
        if not raw:
            logger.error("caixa.fetch_failed", url=source_url)
        return raw

    def _try_playwright(self, url: str) -> bytes:
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        except ImportError:
            logger.error("caixa.playwright_not_installed")
            return b""

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
                context = browser.new_context(
                    user_agent=_BROWSER_HEADERS["User-Agent"],
                    locale="pt-BR",
                    extra_http_headers={
                        "Accept-Language": _BROWSER_HEADERS["Accept-Language"],
                    },
                )
                context.add_init_script(_STEALTH_SCRIPT)
                page = context.new_page()

                # Visitar a home primeiro para resolver o challenge Radware Bot Manager
                logger.info("caixa.playwright_home")
                page.goto(CAIXA_HOME_URL, wait_until="networkidle", timeout=30_000)
                time.sleep(2)

                # Baixar o CSV via expect_download
                logger.info("caixa.playwright_download", url=url)
                with tempfile.TemporaryDirectory() as tmpdir:
                    context.set_default_timeout(60_000)
                    with page.expect_download(timeout=60_000) as dl_info:
                        page.goto(url)
                    dl = dl_info.value
                    dest = Path(tmpdir) / "lista.csv"
                    dl.save_as(str(dest))
                    content = dest.read_bytes()

                browser.close()

                # Se recebemos HTML em vez de CSV, a proteção bloqueou
                if content[:5] in (b"<html", b"<!DOC", b"<HEAD", b"<head"):
                    logger.warning("caixa.playwright_got_html", url=url, size=len(content))
                    return b""

                logger.info("caixa.playwright_ok", url=url, size=len(content))
                return content

        except PWTimeout:
            logger.warning("caixa.playwright_timeout", url=url)
            return b""
        except Exception as exc:
            logger.error("caixa.playwright_failed", url=url, error=str(exc))
            return b""

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        uf = source_url.split("_")[-1].replace(".csv", "").replace(".xlsx", "")
        yield from self.parser.parse(raw_bytes, source_url, uf)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
