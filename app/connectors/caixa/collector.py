import time
import httpx
from typing import Iterator
from app.connectors.base import BankConnector, RawProperty
from app.connectors.caixa.parser import CaixaParser
from app.connectors.caixa.normalizer import CaixaNormalizer
from app.core.config import get_settings
from app.core.logging import logger

# UFs disponíveis no portal Caixa
CAIXA_UFS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
    "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
    "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]

CAIXA_LIST_URL = (
    "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{uf}.xlsx"
)


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
        raw = self._try_requests(source_url)
        if not raw:
            raw = self._try_playwright(source_url)
        return raw

    def _try_requests(self, url: str) -> bytes:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; RadarImovel/1.0; "
                "+https://radarimovel.com.br/bot)"
            )
        }
        delay_s = self.settings.caixa_request_delay_ms / 1000
        for attempt in range(1, self.settings.caixa_max_retries + 1):
            try:
                time.sleep(delay_s)
                response = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
                response.raise_for_status()
                if response.content:
                    return response.content
            except Exception as exc:
                logger.warning("caixa.fetch_attempt_failed", url=url, attempt=attempt, error=str(exc))
        return b""

    def _try_playwright(self, url: str) -> bytes:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                with page.expect_download() as download_info:
                    page.goto(url)
                download = download_info.value
                return download.path().read_bytes() if download.path() else b""
        except Exception as exc:
            logger.error("caixa.playwright_failed", url=url, error=str(exc))
            return b""

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        uf = source_url.split("_")[-1].replace(".xlsx", "")
        yield from self.parser.parse(raw_bytes, source_url, uf)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
