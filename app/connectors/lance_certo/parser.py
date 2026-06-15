"""Parser HTML do Lance Certo Leilões."""
from __future__ import annotations

import re
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.core.logging import logger

_SOURCE_NAME = "lance_certo"


class LanceCertoParser:
    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            return
        soup = BeautifulSoup(raw_bytes, "html.parser")

        items = (
            soup.select(".auction-item")
            or soup.select(".lote-item")
            or soup.select("[data-lote-id]")
            or soup.select(".card-leilao")
            or soup.select("article.lote")
        )

        if not items:
            logger.debug("lance_certo.no_items", url=source_url)
            return

        for item in items:
            try:
                yield self._parse_item(item, source_url)
            except Exception as exc:
                logger.warning("lance_certo.item_error", error=str(exc))
                continue

    def _parse_item(self, item, source_url: str) -> RawProperty:
        title = self._text(item, [".title", "h2", "h3", ".lote-title", ".descricao"])
        city_state = self._text(item, [".location", ".cidade", ".endereco", ".local"])
        city, state = self._split_city_state(city_state)
        price_text = self._text(item, [".price", ".valor", ".lance-inicial", ".valor-minimo"])
        appraisal_text = self._text(item, [".appraisal", ".avaliacao", ".valor-avaliacao"])
        date_text = self._text(item, [".date", ".data-leilao", ".data"])
        link = self._href(item)
        process_text = self._text(item, [".processo", ".numero-processo", "[data-processo]"])
        lot_id = item.get("data-lote-id") or item.get("id") or ""

        external_code = str(lot_id) or re.sub(r"\D", "", process_text or "")[:50] or title[:30]

        return RawProperty(
            external_code=external_code,
            source_url=link or source_url,
            bank_code="lance_certo",
            source_name=_SOURCE_NAME,
            raw_data={
                "title": title,
                "city": city,
                "state": state,
                "current_value": price_text,
                "appraisal_value": appraisal_text,
                "auction_date": date_text,
                "official_url": link or source_url,
                "process_number": process_text,
            },
        )

    @staticmethod
    def _text(item, selectors: list[str]) -> str | None:
        for sel in selectors:
            el = item.select_one(sel)
            if el:
                t = el.get_text(strip=True)
                if t:
                    return t
        return None

    @staticmethod
    def _href(item) -> str | None:
        a = item.select_one("a[href]")
        if not a:
            return None
        href = a.get("href", "")
        if href.startswith("http"):
            return href
        return f"https://www.lancecerto.com.br{href}"

    @staticmethod
    def _split_city_state(text: str | None) -> tuple[str, str]:
        if not text:
            return "", "BR"
        parts = re.split(r"[/,\-–]", text.strip())
        city = parts[0].strip() if parts else ""
        state = parts[-1].strip().upper()[:2] if len(parts) > 1 else "BR"
        return city, state
