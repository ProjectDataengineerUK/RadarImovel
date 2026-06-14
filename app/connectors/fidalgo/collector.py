"""Connector Fidalgo Leilões (fidalgoleiloes.com.br) — leiloeiro SP.

Estrutura: homepage lista leilões ativos via links /leilao.php?idLeilao=N.
Cada página de leilão contém N lotes (.lotePadrao) com preço e descrição.
"""
import re
from collections.abc import Iterator

import httpx

from app.connectors.base import BankConnector, RawProperty
from app.connectors.fidalgo.normalizer import FidalgoNormalizer
from app.connectors.fidalgo.parser import FidalgoParser
from app.connectors.playwright_utils import fetch_with_playwright
from app.core.logging import logger

FIDALGO_BASE_URL = "https://www.fidalgoleiloes.com.br"
FIDALGO_HOME_URL = "https://www.fidalgoleiloes.com.br/"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


class FidalgoConnector(BankConnector):
    bank_code = "fidalgo"
    source_code = "fidalgo"
    source_type = "auctioneer"
    tos_compliant = False

    def __init__(self, uf: str | None = None):
        self.uf = uf
        self.parser = FidalgoParser()
        self.normalizer = FidalgoNormalizer()

    def discover_sources(self) -> list[str]:
        # Homepage blocks httpx (403); Playwright bypasses bot detection.
        html_bytes = fetch_with_playwright(FIDALGO_HOME_URL)
        if not html_bytes:
            logger.error("fidalgo.discover_failed", error="playwright returned empty")
            return []
        try:
            html = html_bytes.decode("utf-8", errors="replace")
            ids = re.findall(r"leilao\.php\?idLeilao=(\d+)", html)
            unique_ids = list(dict.fromkeys(ids))
            logger.info("fidalgo.discover_sources", count=len(unique_ids))
            return [f"{FIDALGO_BASE_URL}/leilao.php?idLeilao={id_}" for id_ in unique_ids]
        except Exception as exc:
            logger.error("fidalgo.discover_failed", error=str(exc))
            return []

    def fetch_raw(self, source_url: str) -> bytes:
        try:
            with httpx.Client(headers=_HEADERS, timeout=30, follow_redirects=True) as client:
                resp = client.get(source_url)
                resp.raise_for_status()
                content = resp.content
        except Exception as exc:
            logger.error("fidalgo.fetch_failed", url=source_url, error=str(exc))
            return b""
        if not content or b"captcha" in content[:512].lower():
            logger.warning("fidalgo.fetch_blocked", url=source_url)
            return b""
        logger.info("fidalgo.fetch_ok", url=source_url, size=len(content))
        return content

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self.parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
