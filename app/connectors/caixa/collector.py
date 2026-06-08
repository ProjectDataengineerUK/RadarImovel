import time
from collections.abc import Iterator

import httpx

from app.connectors.base import BankConnector, RawProperty
from app.connectors.caixa.normalizer import CaixaNormalizer
from app.connectors.caixa.parser import CaixaParser
from app.core.config import get_settings
from app.core.logging import logger

CAIXA_UFS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
    "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
    "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]

CAIXA_LIST_URL = "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{uf}.csv"
CAIXA_HOME_URL = "https://venda-imoveis.caixa.gov.br/"

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# Patches injected before every page load to hide Playwright fingerprints
_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR','pt','en-US']});
window.chrome = {runtime: {}};
const origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (params) =>
    params.name === 'notifications'
        ? Promise.resolve({state: Notification.permission})
        : origQuery(params);
"""


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
        raw = self._fetch_with_playwright_cookies(source_url)
        if not raw:
            logger.error("caixa.fetch_failed", url=source_url)
        return raw

    def _fetch_with_playwright_cookies(self, csv_url: str) -> bytes:
        """
        1. Playwright visita a home da Caixa → resolve o challenge Radware (JS).
        2. Extrai os cookies validados do contexto do browser.
        3. httpx faz o GET do CSV usando esses cookies — mesmo request que o browser faria.
        Essa abordagem é mais confiável que expect_download porque não depende de
        dialog de download e separa o challenge da transferência de bytes.
        """
        try:
            from playwright.sync_api import sync_playwright
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
                        "--disable-setuid-sandbox",
                    ],
                )
                context = browser.new_context(
                    user_agent=_UA,
                    locale="pt-BR",
                    viewport={"width": 1280, "height": 800},
                    extra_http_headers={"Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8"},
                )
                context.add_init_script(_STEALTH_SCRIPT)
                page = context.new_page()

                # Visitar home para resolver o challenge Radware
                logger.info("caixa.playwright_challenge_start")
                page.goto(CAIXA_HOME_URL, wait_until="domcontentloaded", timeout=45_000)
                # Simular comportamento humano mínimo
                page.mouse.move(400, 300)
                page.mouse.move(600, 400)
                page.evaluate("window.scrollBy(0, 200)")
                time.sleep(3)

                # Extrair cookies resolvidos
                cookies = context.cookies()
                browser.close()

            if not cookies:
                logger.warning("caixa.playwright_no_cookies")
                return b""

            # Converter para dict httpx
            cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
            logger.info("caixa.playwright_cookies_ok", count=len(cookies))

            # Baixar CSV com os cookies validados
            headers = {
                "User-Agent": _UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
                "Referer": CAIXA_HOME_URL,
                "Cookie": cookie_header,
            }
            resp = httpx.get(csv_url, headers=headers, timeout=60, follow_redirects=True)
            resp.raise_for_status()

            content = resp.content
            if content[:5].lower() in (b"<html", b"<!doc"):
                logger.warning("caixa.got_html_after_challenge", url=csv_url, size=len(content))
                return b""

            logger.info("caixa.fetch_ok", url=csv_url, size=len(content))
            return content

        except Exception as exc:
            logger.error("caixa.fetch_error", url=csv_url, error=str(exc))
            return b""

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        uf = source_url.split("_")[-1].replace(".csv", "").replace(".xlsx", "")
        yield from self.parser.parse(raw_bytes, source_url, uf)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
