"""Connector Banco da Amazônia (basa).

Página de editais de venda de bens (HTML índice) → links de editais PDF
(leilão/praça pública). PDFs extraídos com pdfplumber. Hipóteses a validar.
"""
import re
from collections.abc import Iterator

import httpx
from bs4 import BeautifulSoup

from app.connectors.basa.normalizer import BASANormalizer
from app.connectors.basa.parser import BASAParser
from app.connectors.base import BankConnector, RawProperty
from app.core.logging import logger

BASA_INDEX_URL = "https://www.bancoamazonia.com.br/imoveis-e-bens"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/pdf,application/xhtml+xml;q=0.9,*/*;q=0.8",
}


class BASAConnector(BankConnector):
    bank_code = "basa"

    def __init__(self, uf: str | None = None):
        self.uf = uf
        self.parser = BASAParser()
        self.normalizer = BASANormalizer()

    def discover_sources(self) -> list[str]:
        sources = [BASA_INDEX_URL]
        index_bytes = self.fetch_raw(BASA_INDEX_URL)
        sources.extend(self._extract_pdf_links(index_bytes, BASA_INDEX_URL))
        return sources

    def _extract_pdf_links(self, raw_bytes: bytes, base_url: str) -> list[str]:
        if not raw_bytes or raw_bytes[:4] == b"%PDF":
            return []
        try:
            soup = BeautifulSoup(raw_bytes, "lxml")
        except Exception as exc:
            logger.error("basa.index_soup_failed", error=str(exc))
            return []
        links: list[str] = []
        for a in soup.select("a[href]"):
            href = str(a.get("href", "")).strip()
            if re.search(r"\.pdf($|\?)", href, re.IGNORECASE):
                if not href.startswith("http"):
                    href = base_url.rsplit("/", 1)[0] + "/" + href.lstrip("/")
                links.append(href)
        logger.info("basa.index_pdf_links", count=len(links))
        return links

    def fetch_raw(self, source_url: str) -> bytes:
        try:
            with httpx.Client(
                headers=_HEADERS, timeout=45, follow_redirects=True
            ) as client:
                resp = client.get(source_url)
                resp.raise_for_status()
                content = resp.content
        except Exception as exc:
            logger.error("basa.fetch_failed", url=source_url, error=str(exc))
            return b""

        if content[:4] != b"%PDF" and content[:5].lower() in (b"<html", b"<!doc"):
            head = content[:512].lower()
            if b"captcha" in head or b"challenge" in head:
                logger.warning("basa.fetch_got_challenge", url=source_url)
                return b""
        logger.info("basa.fetch_ok", url=source_url, size=len(content))
        return content

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self.parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
