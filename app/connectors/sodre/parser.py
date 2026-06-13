"""Parser HTML do Sodré Santoro (sodresantoro.com.br).

Sodré requer Playwright (bloqueia httpx). Estrutura interna desconhecida sem
acesso ao HTML renderizado; parser tenta múltiplos seletores comuns para
leiloeiros brasileiros e loga as classes presentes para diagnóstico quando
nenhum seletor funciona.
"""
import re
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.core.logging import logger

_BASE_URL = "https://www.sodresantoro.com.br"
_SOURCE_NAME = "sodre_imoveis"

# Ordered by likelihood based on typical Brazilian auctioneer sites
_CARD_SELECTORS = [
    ".card-lote",
    ".lote-card",
    ".lot-card",
    ".card-bem",
    ".item-lote",
    ".lote-item",
    ".auction-lot",
    ".auction-item",
    ".card.lote",
    "article.lote",
    "article.card",
    "li.lote",
    "tr[data-id]",
    "tr[data-lote]",
    "[data-lote-id]",
    "[data-bem-id]",
    ".item-leilao",
]


class SodreParser:
    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            return
        soup = BeautifulSoup(raw_bytes, "html.parser")

        cards = []
        matched_selector = None
        for sel in _CARD_SELECTORS:
            found = soup.select(sel)
            if found:
                cards = found
                matched_selector = sel
                break

        if not cards:
            classes_found = sorted({
                cl
                for tag in soup.find_all(True)
                for cl in (tag.get("class") or [])
                if any(
                    k in cl.lower()
                    for k in ("lot", "lote", "bem", "item", "card", "imovel", "auction")
                )
            })
            logger.warning(
                "sodre.parser.no_cards",
                url=source_url,
                html_size=len(raw_bytes),
                relevant_classes=classes_found[:30],
            )
            return

        logger.info("sodre.parser.matched", selector=matched_selector, count=len(cards))
        for card in cards:
            try:
                yield from self._parse_card(card, source_url)
            except Exception as exc:
                logger.warning("sodre.parser.card_error", error=str(exc))

    def _parse_card(self, card, source_url: str) -> Iterator[RawProperty]:
        ext = (
            card.get("data-id")
            or card.get("data-lote")
            or card.get("data-lote-id")
            or card.get("data-bem-id")
            or card.get("data-ref", "")
        )
        if not ext:
            link = card.select_one("a[href]")
            if link:
                m = re.search(r"(?:id|lote|bem)[=/](\d+)", link["href"], re.I)
                if m:
                    ext = m.group(1)
        if not ext:
            return

        link_tag = card.select_one("a[href]")
        url = link_tag["href"] if link_tag else source_url
        if url.startswith("/"):
            url = _BASE_URL + url

        yield RawProperty(
            external_code=str(ext).strip(),
            source_url=url,
            bank_code="sodre",
            source_name=_SOURCE_NAME,
            raw_data={
                "external_code": str(ext).strip(),
                "title": _t(
                    card, "h2, h3, h4, .titulo, .title, .descricao, .lote-desc"
                ),
                "current_value": _t(
                    card,
                    ".lance-inicial, .valor-inicial, .preco, .valor, "
                    "[data-lance], [data-valor], .lance",
                ),
                "appraisal_value": _t(
                    card, ".avaliacao, [data-avaliacao], .valor-avaliacao"
                ),
                "address": _t(
                    card, ".endereco, .localizacao, .local, .address, [data-endereco]"
                ),
                "city": _t(card, ".cidade, .city, [data-cidade]"),
                "state": _t(card, ".estado, .uf, .state, [data-uf]"),
                "sale_modality": _t(card, ".modalidade, .tipo-leilao, .modality"),
                "auction_date": _t(
                    card, ".data-leilao, .data, time, [data-data], .encerramento"
                ),
                "property_type": _t(card, ".tipo, .type, [data-tipo], .categoria"),
                "area_total": _t(card, ".area, [data-area], .metragem"),
                "occupancy_status": _t(card, ".ocupacao, [data-ocupacao], .situacao"),
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
