import sys
import time
from collections.abc import Iterator

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

_IS_TTY = sys.stdout.isatty()


def _fmt_bytes(n: int) -> str:
    if n >= 1_048_576:
        return f"{n / 1_048_576:.1f} MB"
    if n >= 1_024:
        return f"{n / 1_024:.1f} KB"
    return f"{n} B"


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
        Roda o Playwright em thread separada para evitar conflito com asyncio.
        expect_download usa asyncio internamente — falha se já há um loop rodando.
        """
        import concurrent.futures

        uf = csv_url.split("_")[-1].replace(".csv", "")
        start = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self._playwright_download_in_thread, csv_url)
            try:
                content = future.result(timeout=200)
            except Exception as exc:
                logger.error("caixa.fetch_error", url=csv_url, error=str(exc))
                return b""

        if content is None:
            return b""

        if content[:20].lstrip().lower().startswith(b"<"):
            logger.warning("caixa.got_html_after_challenge", url=csv_url, size=len(content))
            return b""

        elapsed = time.time() - start
        size = len(content)
        if _IS_TTY:
            speed = size / elapsed if elapsed > 0 else 0
            print(f"  ✓ CSV {uf}  {_fmt_bytes(size)}  ({elapsed:.1f}s, {_fmt_bytes(int(speed))}/s)")
        logger.info("caixa.fetch_ok", uf=uf, bytes=size, size=_fmt_bytes(size), elapsed_s=round(elapsed, 1))
        return content

    def _playwright_download_in_thread(self, csv_url: str) -> bytes | None:
        """
        Executa em thread própria (sem asyncio) → sync_playwright + expect_download funcionam.
        Fluxo: home → challenge Radware → cookies → goto(csv_url) → download.
        """
        import pathlib

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("caixa.playwright_not_installed")
            return None

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
                    accept_downloads=True,
                )
                context.add_init_script(_STEALTH_SCRIPT)
                page = context.new_page()

                logger.info("caixa.playwright_challenge_start")
                page.goto(CAIXA_HOME_URL, wait_until="domcontentloaded", timeout=45_000)
                page.mouse.move(400, 300)
                page.mouse.move(600, 400)
                page.evaluate("window.scrollBy(0, 200)")
                time.sleep(3)

                cookies = context.cookies()
                logger.info("caixa.playwright_cookies_ok", count=len(cookies))

                with page.expect_download(timeout=120_000) as dl_info:
                    page.goto(csv_url, wait_until="commit", timeout=120_000)

                content = pathlib.Path(dl_info.value.path()).read_bytes()
                browser.close()
                return content

        except Exception as exc:
            logger.error("caixa.fetch_error", url=csv_url, error=str(exc))
            return None

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        uf = source_url.split("_")[-1].replace(".csv", "").replace(".xlsx", "")
        yield from self.parser.parse(raw_bytes, source_url, uf)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
