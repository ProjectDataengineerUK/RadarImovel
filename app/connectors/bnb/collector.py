"""Connector Banco do Nordeste (bnb).

Página "Bens à Venda" (HTML) + PDF de relação de imóveis. Detecta content-type
em fetch_raw. URLs e formato são hipóteses a validar no build.
"""
from collections.abc import Iterator

import httpx

from app.connectors.base import BankConnector, RawProperty
from app.connectors.bnb.normalizer import BNBNormalizer
from app.connectors.bnb.parser import BNBParser
from app.core.logging import logger

BNB_LIST_URL = "https://www.bnb.gov.br/bens-em-oferta"

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
        return [BNB_LIST_URL]

    def fetch_raw(self, source_url: str) -> bytes:
        try:
            with httpx.Client(
                headers=_HEADERS, timeout=45, follow_redirects=True
            ) as client:
                resp = client.get(source_url)
                resp.raise_for_status()
                content = resp.content
                content_type = resp.headers.get("content-type", "")
        except Exception as exc:
            logger.error("bnb.fetch_failed", url=source_url, error=str(exc))
            return b""

        is_pdf = content[:4] == b"%PDF" or "application/pdf" in content_type
        if not is_pdf and content[:5].lower() in (b"<html", b"<!doc"):
            head = content[:512].lower()
            if b"captcha" in head or b"challenge" in head:
                logger.warning("bnb.fetch_got_challenge", url=source_url)
                return b""
        logger.info("bnb.fetch_ok", url=source_url, size=len(content), pdf=is_pdf)
        return content

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        yield from self.parser.parse(raw_bytes, source_url)

    def normalize(self, raw: RawProperty) -> dict:
        return self.normalizer.normalize(raw)
