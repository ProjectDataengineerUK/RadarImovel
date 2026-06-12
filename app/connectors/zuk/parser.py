"""Parser HTML do Portal Zuk.

Seletores baseados na estrutura observada em 2026-06 (cards de imóvel).
Adaptar seletores se o layout mudar.
"""
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.core.logging import logger

_SOURCE_NAME = "zuk_imoveis"


class ZukParser:
    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            return

        soup = BeautifulSoup(raw_bytes, "html.parser")

        # Zuk usa cards com data-id ou classe "property-card" / "imovel-card"
        cards = (
            soup.select("[data-id]")
            or soup.select(".property-card")
            or soup.select(".imovel-card")
            or soup.select("article.card")
        )

        if not cards:
            logger.warning("zuk.parser.no_cards", url=source_url)
            return

        for card in cards:
            try:
                yield from self._parse_card(card, source_url)
            except Exception as exc:
                logger.warning("zuk.parser.card_error", url=source_url, error=str(exc))

    def _parse_card(self, card, source_url: str) -> Iterator[RawProperty]:
        ext_code = (
            card.get("data-id")
            or card.get("data-cod")
            or card.get("data-ref", "")
        )
        if not ext_code:
            return

        link_tag = card.select_one("a[href]")
        detail_url = str(link_tag["href"]) if link_tag else source_url
        if detail_url.startswith("/"):
            detail_url = "https://www.portalzuk.com.br" + detail_url

        title = _text(card, ".title, .titulo, h2, h3")
        price_raw = _text(card, ".price, .preco, [data-preco], .valor")
        address_raw = _text(card, ".address, .endereco, .localizacao")
        modality_raw = _text(card, ".modality, .modalidade, .tipo-venda")
        auction_raw = _text(card, ".auction-date, .data-leilao, .data")
        state_raw = _text(card, ".state, .uf, [data-uf]")
        city_raw = _text(card, ".city, .cidade, [data-cidade]")
        type_raw = _text(card, ".type, .tipo, [data-tipo]")
        area_raw = _text(card, ".area, [data-area]")
        bedrooms_raw = _text(card, ".bedrooms, .quartos, [data-quartos]")
        img_tag = card.select_one("img[src]")
        photo_url = img_tag["src"] if img_tag else None

        yield RawProperty(
            external_code=str(ext_code).strip(),
            source_url=detail_url,
            bank_code="zuk",
            source_name=_SOURCE_NAME,
            raw_data={
                "title": title,
                "current_value": price_raw,
                "address": address_raw,
                "sale_modality": modality_raw,
                "auction_date": auction_raw,
                "state": state_raw,
                "city": city_raw,
                "property_type": type_raw,
                "area_total": area_raw,
                "bedrooms": bedrooms_raw,
                "official_url": detail_url,
                "photo_url": photo_url,
                "external_code": str(ext_code).strip(),
            },
        )


def _text(tag, selector: str) -> str | None:
    for sel in selector.split(","):
        el = tag.select_one(sel.strip())
        if el:
            return el.get_text(strip=True) or None
    return None
