"""Parser HTML do Fidalgo Leilões."""
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.core.logging import logger

_BASE_URL = "https://www.fidalgoleiloes.com.br"
_SOURCE_NAME = "fidalgo_imoveis"


class FidalgoParser:
    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            return
        soup = BeautifulSoup(raw_bytes, "html.parser")
        cards = (
            soup.select(".property-item")
            or soup.select(".imovel-item")
            or soup.select("[data-ref]")
            or soup.select("article")
        )
        if not cards:
            logger.warning("fidalgo.parser.no_cards", url=source_url)
            return
        for card in cards:
            try:
                yield from self._parse_card(card, source_url)
            except Exception as exc:
                logger.warning("fidalgo.parser.card_error", error=str(exc))

    def _parse_card(self, card, source_url: str) -> Iterator[RawProperty]:
        ext = (card.get("data-ref") or card.get("data-id") or card.get("data-lote", "")).strip()
        if not ext:
            return
        link_tag = card.select_one("a[href]")
        url = link_tag["href"] if link_tag else source_url
        if url.startswith("/"):
            url = _BASE_URL + url

        yield RawProperty(
            external_code=ext,
            source_url=url,
            bank_code="fidalgo",
            source_name=_SOURCE_NAME,
            raw_data={
                "external_code": ext,
                "title": _t(card, "h2, h3, .titulo, .title"),
                "current_value": _t(card, ".preco, .valor, .lance, [data-valor]"),
                "appraisal_value": _t(card, ".avaliacao, [data-avaliacao]"),
                "address": _t(card, ".endereco, .localizacao"),
                "city": _t(card, ".cidade, [data-cidade]"),
                "state": _t(card, ".uf, [data-uf]"),
                "sale_modality": _t(card, ".modalidade, .tipo"),
                "auction_date": _t(card, ".data, time, [data-data]"),
                "property_type": _t(card, ".tipo-imovel, [data-tipo]"),
                "area_total": _t(card, ".area, [data-area]"),
                "official_url": url,
                "photo_url": (card.select_one("img[src]") or {}).get("src"),
            },
        )


def _t(tag, selector: str) -> str | None:
    for s in selector.split(","):
        el = tag.select_one(s.strip())
        if el:
            return el.get_text(strip=True) or None
    return None
