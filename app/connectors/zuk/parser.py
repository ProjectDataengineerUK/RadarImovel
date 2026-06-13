"""Parser HTML do Portal Zuk (portalzuk.com.br).

Estrutura observada em 2026-06: listagem em /leilao-de-imoveis?pagina=N retorna
30 cards .card-property por página. External code extraído do slug de URL.
"""
import re
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.core.logging import logger

_BASE_URL = "https://www.portalzuk.com.br"
_SOURCE_NAME = "zuk_imoveis"


class ZukParser:
    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            return
        soup = BeautifulSoup(raw_bytes, "html.parser")
        cards = soup.select(".card-property")
        if not cards:
            logger.warning("zuk.parser.no_cards", url=source_url)
            return
        for card in cards:
            try:
                yield from self._parse_card(card, source_url)
            except Exception as exc:
                logger.warning("zuk.parser.card_error", url=source_url, error=str(exc))

    def _parse_card(self, card, source_url: str) -> Iterator[RawProperty]:
        link_tag = card.select_one("a[href*='/imovel/']")
        if not link_tag:
            return
        url = str(link_tag["href"])
        if url.startswith("/"):
            url = _BASE_URL + url

        # External code from last URL segment: "36502-226888"
        code_match = re.search(r"/(\d+-\d+)(?:\?|$)", url)
        ext = code_match.group(1) if code_match else ""
        if not ext:
            return

        # Address from .card-property-address ("City / UF- NeighborhoodStreet")
        addr_el = card.select_one(".card-property-address")
        addr_txt = addr_el.get_text(" ", strip=True) if addr_el else ""

        # Extract city and state from address prefix "City / UF"
        city, state = "", ""
        city_state_match = re.match(r"^([^/]+)/\s*([A-Z]{2})", addr_txt)
        if city_state_match:
            city = city_state_match.group(1).strip()
            state = city_state_match.group(2).strip()

        # Price from .card-property-price-value
        price_el = card.select_one(".card-property-price-value")
        current_value = price_el.get_text(strip=True) if price_el else None

        # Area from .card-property-info
        info_el = card.select_one(".card-property-info-label")
        area = info_el.get_text(strip=True) if info_el else None

        img_tag = card.select_one("img[src]")
        photo = img_tag["src"] if img_tag else None

        yield RawProperty(
            external_code=ext,
            source_url=url,
            bank_code="zuk",
            source_name=_SOURCE_NAME,
            raw_data={
                "external_code": ext,
                "title": addr_txt,
                "address": addr_txt,
                "city": city,
                "state": state,
                "current_value": current_value,
                "area_total": area,
                "official_url": url,
                "photo_url": photo,
            },
        )
