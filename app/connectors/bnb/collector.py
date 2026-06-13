"""Connector Banco do Nordeste (bnb).

Liferay page has the PDF link in static HTML — no Playwright needed.
discover_sources() fetches the index, extracts the PDF URL, returns it directly.
"""
import re
from collections.abc import Iterator

import httpx
from bs4 import BeautifulSoup

from app.connectors.base import BankConnector, RawProperty
from app.connectors.bnb.normalizer import BNBNormalizer
from app.connectors.bnb.parser import BNBParser
from app.core.logging import logger

BNB_LIST_URL = "https://www.bnb.gov.br/acesso-a-informacao/licitacoes-e-contratos/bens-a-venda"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/pdf,application/xhtml+xml;q=0.9,*/*;q=0.8",
}


class BNBConnector(BankConnector):
    bank_code = "bnb"

    def __init__(self, uf: str | None = None):
        self.uf = uf
        self.parser = BNBParser()
        self.normalizer = BNBNormalizer()

    def discover_sources(self) -> list[str]:
        try:
            with httpx.Client(headers=_HEADERS, timeout=30, follow_redirects=True) as client:
                resp = client.get(BNB_LIST_URL)
                resp.raise_for_status()
                html = resp.text
        except Exception as exc:
            logger.error("bnb.discover_failed", url=BNB_LIST_URL, error=str(exc))
            return []

        soup = BeautifulSoup(html, "lxml")
        pdf_links: list[str] = []
        for a in soup.find_all("a", href=True):
            href = str(a["href"]).strip()
            if re.search(r"\.pdf", href, re.IGNORECASE):
                if not href.startswith("http"):
                    href = "https://www.bnb.gov.br" + href
                pdf_links.append(href)

        if not pdf_links:
            logger.warning("bnb.discover_no_pdf", url=BNB_LIST_URL)
            return []

        logger.info("bnb.discover_pdf", count=len(pdf_links))
        return pdf_links

    def fetch_raw(self, source_url: str) -> bytes:
        try:
            with httpx.Client(headers=_HEADERS, timeout=60, follow_redirects=True) as client:
                resp = client.get(source_url)
                resp.raise_for_status()
                content = resp.content
        except Exception as exc:
            logger.error("bnb.fetch_failed", url=source_url, error=str(exc))
            return b""

        head = content[:512].lower()
        if b"captcha" in head or b"challenge" in head:
            logger.warning("bnb.fetch_got_challenge", url=source_url)
            return b""
        logger.info("bnb.fetch_ok", url=source_url, size=len(content))
        return content

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self.parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
