"""Parser HTML do Frazão Leilões."""
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.core.logging import logger

_BASE_URL = "https://www.frazaoleiloes.com.br"
_SOURCE_NAME = "frazao_imoveis"


class FrazaoParser:
    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            return
        soup = BeautifulSoup(raw_bytes, "html.parser")
        cards = (
            soup.select(".lote-card")
            or soup.select(".item-lote")
            or soup.select("[data-lote]")
            or soup.select("article.card")
        )
        if not cards:
            logger.warning("frazao.parser.no_cards", url=source_url)
            return
        for card in cards:
            try:
                yield from self._parse_card(card, source_url)
            except Exception as exc:
                logger.warning("frazao.parser.card_error", error=str(exc))

    def _parse_card(self, card, source_url: str) -> Iterator[RawProperty]:
        ext = (card.get("data-lote") or card.get("data-id") or card.get("data-ref", "")).strip()
        if not ext:
            return
        link_tag = card.select_one("a[href]")
        url = link_tag["href"] if link_tag else source_url
        if url.startswith("/"):
            url = _BASE_URL + url

        yield RawProperty(
            external_code=ext,
            source_url=url,
            bank_code="frazao",
            source_name=_SOURCE_NAME,
            raw_data={
                "external_code": ext,
                "title": _t(card, "h2, h3, .titulo, .title, .nome"),
                "current_value": _t(card, ".lance, .preco, .valor, [data-lance]"),
                "appraisal_value": _t(card, ".avaliacao, [data-avaliacao], .valor-avaliacao"),
                "address": _t(card, ".endereco, .local, .localizacao"),
                "city": _t(card, ".cidade, [data-cidade]"),
                "state": _t(card, ".uf, [data-uf], .estado"),
                "sale_modality": _t(card, ".modalidade, .tipo-venda"),
                "auction_date": _t(card, ".data-leilao, time, [data-data]"),
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
