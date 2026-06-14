"""Parser HTML do Frazão Leilões (frazaoleiloes.com.br).

Após renderização JS, cada lote aparece como div.item-bid dentro de
#leilao-lista-lote. O link tem atributos data-lote-id, data-tipo e data-addr.
O preço está em input[name="price"] dentro do mesmo item-bid.
"""
import re
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
        items = soup.select("#leilao-lista-lote .item-bid")
        if not items:
            items = soup.select(".item-bid")
        if not items:
            # Diagnose: log container presence and all top classes
            has_container = bool(soup.select_one("#content_list_lote"))
            all_ids = [t.get("id") for t in soup.find_all(id=True)][:20]
            top_classes = sorted({
                cl for tag in soup.find_all(True)
                for cl in (tag.get("class") or [])
            })[:40]
            # Log first link hrefs to find card URL pattern
            hrefs = [a.get("href","") for a in soup.select("a[href]") if "/lote" in a.get("href","")][:5]
            logger.warning(
                "frazao.parser.no_cards",
                url=source_url,
                has_content_list_lote=has_container,
                ids=all_ids,
                top_classes=top_classes,
                lote_hrefs=hrefs,
            )
            return
        for item in items:
            try:
                yield from self._parse_item(item, source_url)
            except Exception as exc:
                logger.warning("frazao.parser.card_error", error=str(exc))

    def _parse_item(self, item, source_url: str) -> Iterator[RawProperty]:
        link_tag = item.select_one("a[data-lote-id]")
        if not link_tag:
            return
        lot_id = str(link_tag.get("data-lote-id", "")).strip()
        if not lot_id:
            return

        href = str(link_tag.get("href", ""))
        url = (f"{_BASE_URL}{href}" if href.startswith("/") else href) or source_url

        title_el = item.select_one(".lote-information")
        title = title_el.get_text(strip=True) if title_el else None

        address = str(link_tag.get("data-addr", "")).strip() or None
        prop_type = str(link_tag.get("data-tipo", "")).strip() or None

        # Extract city/state from last segment of data-addr: "...Rua X - Recife/PE"
        city, state = "", ""
        if address:
            city_state_match = re.search(r"-\s*([^/\-]+)/([A-Z]{2})\s*$", address)
            if city_state_match:
                city = city_state_match.group(1).strip()
                state = city_state_match.group(2).strip()

        price_input = item.select_one("input[name='price']")
        current_value = price_input.get("value") if price_input else None

        img_tag = item.select_one("img[src]")
        photo = img_tag["src"] if img_tag else None
        if photo and photo.startswith("/"):
            photo = _BASE_URL + photo

        yield RawProperty(
            external_code=lot_id,
            source_url=url,
            bank_code="frazao",
            source_name=_SOURCE_NAME,
            raw_data={
                "external_code": lot_id,
                "title": title,
                "address": address,
                "city": city,
                "state": state,
                "property_type": prop_type,
                "current_value": current_value,
                "official_url": url,
                "photo_url": photo,
            },
        )
