import sys
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
_CHUNK_SIZE = 65_536  # 64 KB


def _fmt_bytes(n: int) -> str:
    if n >= 1_048_576:
        return f"{n / 1_048_576:.1f} MB"
    if n >= 1_024:
        return f"{n / 1_024:.1f} KB"
    return f"{n} B"


def _render_bar(pct: float, width: int = 30) -> str:
    filled = int(width * pct / 100)
    return "█" * filled + "░" * (width - filled)


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
        3. httpx streaming baixa o CSV com progresso visível no terminal.
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

                logger.info("caixa.playwright_challenge_start")
                page.goto(CAIXA_HOME_URL, wait_until="domcontentloaded", timeout=45_000)
                page.mouse.move(400, 300)
                page.mouse.move(600, 400)
                page.evaluate("window.scrollBy(0, 200)")
                time.sleep(3)

                cookies = context.cookies()
                browser.close()

            if not cookies:
                logger.warning("caixa.playwright_no_cookies")
                return b""

            cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
            logger.info("caixa.playwright_cookies_ok", count=len(cookies))

            return self._stream_download(csv_url, cookie_header)

        except Exception as exc:
            logger.error("caixa.fetch_error", url=csv_url, error=str(exc))
            return b""

    def _stream_download(self, url: str, cookie_header: str) -> bytes:
        headers = {
            "User-Agent": _UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
            "Referer": CAIXA_HOME_URL,
            "Cookie": cookie_header,
        }
        uf = url.split("_")[-1].replace(".csv", "")
        chunks: list[bytes] = []
        downloaded = 0
        total = 0
        start = time.time()
        last_logged_pct = -1

        with httpx.stream("GET", url, headers=headers, timeout=120, follow_redirects=True) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))

            if _IS_TTY:
                label = f"  Baixando CSV {uf}"
                sys.stdout.write(f"{label}  [{'░' * 30}]   0%   0 B\r")
                sys.stdout.flush()

            for chunk in resp.iter_bytes(chunk_size=_CHUNK_SIZE):
                chunks.append(chunk)
                downloaded += len(chunk)
                elapsed = time.time() - start

                if _IS_TTY:
                    if total:
                        pct = downloaded / total * 100
                        bar = _render_bar(pct)
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        sys.stdout.write(
                            f"  Baixando CSV {uf}  [{bar}] {pct:3.0f}%"
                            f"  {_fmt_bytes(downloaded)} / {_fmt_bytes(total)}"
                            f"  {_fmt_bytes(int(speed))}/s\r"
                        )
                    else:
                        sys.stdout.write(
                            f"  Baixando CSV {uf}  {_fmt_bytes(downloaded)} baixados...\r"
                        )
                    sys.stdout.flush()
                else:
                    # Cloud Run: log a cada 25%
                    if total:
                        pct = int(downloaded / total * 100)
                        milestone = (pct // 25) * 25
                        if milestone > last_logged_pct:
                            last_logged_pct = milestone
                            logger.info(
                                "caixa.download_progress",
                                uf=uf,
                                pct=milestone,
                                downloaded=_fmt_bytes(downloaded),
                                total=_fmt_bytes(total),
                            )

        elapsed = time.time() - start
        content = b"".join(chunks)

        if _IS_TTY:
            # Limpar a linha e imprimir resultado final
            sys.stdout.write(" " * 90 + "\r")
            total_label = f"/ {_fmt_bytes(total)}" if total else ""
            speed = downloaded / elapsed if elapsed > 0 else 0
            print(
                f"  ✓ CSV {uf}  [{_render_bar(100)}] 100%"
                f"  {_fmt_bytes(downloaded)} {total_label}"
                f"  ({elapsed:.1f}s, {_fmt_bytes(int(speed))}/s)"
            )

        if content[:5].lower() in (b"<html", b"<!doc"):
            logger.warning("caixa.got_html_after_challenge", url=url, size=len(content))
            return b""

        logger.info(
            "caixa.fetch_ok",
            uf=uf,
            bytes=downloaded,
            size=_fmt_bytes(downloaded),
            elapsed_s=round(elapsed, 1),
        )
        return content

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        uf = source_url.split("_")[-1].replace(".csv", "").replace(".xlsx", "")
        yield from self.parser.parse(raw_bytes, source_url, uf)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
