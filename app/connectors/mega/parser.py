"""Parser HTML do Mega Leilões (megaleiloes.com.br).

Estrutura observada em 2026-06: listagem em /imoveis?pagina=N retorna cards .card
com subclasses .card-title, .card-price, .card-locality, .card-number.
"""
import re
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.core.logging import logger

_BASE_URL = "https://www.megaleiloes.com.br"
_SOURCE_NAME = "mega_imoveis"

# Tipo de imóvel extraído do segmento de URL /imoveis/{tipo}/
_TYPE_MAP = {
    "apartamentos": "Apartamento",
    "casas": "Casa",
    "terrenos": "Terreno",
    "comerciais": "Comercial",
    "rurais": "Rural",
    "galpoes": "Galpão",
    "salas": "Sala Comercial",
}


class MegaParser:
    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            return
        soup = BeautifulSoup(raw_bytes, "html.parser")
        cards = soup.select(".card")
        if not cards:
            logger.warning("mega.parser.no_cards", url=source_url)
            return
        for card in cards:
            try:
                yield from self._parse_card(card, source_url)
            except Exception as exc:
                logger.warning("mega.parser.card_error", error=str(exc))

    def _parse_card(self, card, source_url: str) -> Iterator[RawProperty]:
        # External code from .card-number (e.g. "J123892")
        code_el = card.select_one(".card-number")
        ext = code_el.get_text(strip=True) if code_el else ""
        if not ext:
            return

        link_tag = card.select_one("a.card-image, a[href*='/imoveis/']")
        url = str(link_tag["href"]) if link_tag else source_url
        if url.startswith("/"):
            url = _BASE_URL + url

        # City + state from ".card-locality" → "São Vicente, SP"
        loc_el = card.select_one(".card-locality")
        loc_txt = loc_el.get_text(strip=True) if loc_el else ""
        loc_match = re.match(r"^(.+),\s*([A-Z]{2})$", loc_txt)
        city = loc_match.group(1) if loc_match else loc_txt
        state = loc_match.group(2) if loc_match else ""

        # Current value = active instance price (.card-price shows the active bid amount)
        price_el = card.select_one(".card-price")
        current_value = price_el.get_text(strip=True) if price_el else None

        # Appraisal = 1ª Praça value (first instance)
        appraisal_el = card.select_one(".instance.first .card-instance-value")
        appraisal = appraisal_el.get_text(strip=True) if appraisal_el else current_value

        # Discount from .card-down value span
        discount_el = card.select_one(".card-down .value")
        discount = discount_el.get_text(strip=True) if discount_el else None

        # Property type from URL segment
        type_match = re.search(r"/imoveis/([^/]+)/", url)
        prop_type = _TYPE_MAP.get(type_match.group(1), "Imóvel") if type_match else "Imóvel"

        # Title from .card-title
        title_el = card.select_one(".card-title")
        title = title_el.get_text(strip=True) if title_el else None

        # Sale modality (Judicial / Extrajudicial) from .card-instance-title
        modality_el = card.select_one(".card-instance-title")
        modality = modality_el.get_text(strip=True) if modality_el else None

        # Active auction date
        date_el = card.select_one(
            ".instance.active .card-second-instance-date, "
            ".instance.active .card-first-instance-date"
        )
        auction_date = date_el.get_text(strip=True) if date_el else None

        img_tag = card.select_one("img[src]")
        photo = img_tag["src"] if img_tag else None

        yield RawProperty(
            external_code=ext,
            source_url=url,
            bank_code="mega",
            source_name=_SOURCE_NAME,
            raw_data={
                "external_code": ext,
                "title": title,
                "current_value": current_value,
                "appraisal_value": appraisal,
                "discount_percent": discount,
                "city": city,
                "state": state,
                "sale_modality": modality,
                "auction_date": auction_date,
                "property_type": prop_type,
                "official_url": url,
                "photo_url": photo,
            },
        )
