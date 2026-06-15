"""Parser HTML/JSON do Super Leilões."""
from __future__ import annotations

import json
import re
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.core.logging import logger

_SOURCE_NAME = "superleiloes"
_BASE_URL = "https://www.superleiloes.com.br"


class SuperleiloesParser:
    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            return
        text = raw_bytes.decode("utf-8", errors="replace")

        if text.lstrip().startswith("{") or text.lstrip().startswith("["):
            yield from self._parse_json(text, source_url)
        else:
            yield from self._parse_html(raw_bytes, source_url)

    def _parse_json(self, text: str, source_url: str) -> Iterator[RawProperty]:
        try:
            data = json.loads(text)
            items = data if isinstance(data, list) else data.get("items", data.get("lotes", []))
        except Exception:
            logger.warning("superleiloes.json_parse_error", url=source_url)
            return

        for item in items:
            try:
                lot_id = str(item.get("id") or item.get("loteId") or "")
                title = item.get("titulo") or item.get("descricao") or ""
                city = item.get("cidade") or ""
                state = item.get("uf") or item.get("estado") or "BR"
                price = item.get("valorInicial") or item.get("lance") or item.get("valor")
                appraisal = item.get("valorAvaliacao") or item.get("avaliacao")
                date = item.get("dataLeilao") or item.get("data")
                link = item.get("url") or item.get("link") or f"{_BASE_URL}/lote/{lot_id}"
                if not link.startswith("http"):
                    link = _BASE_URL + link
                process_num = item.get("processo") or item.get("numeroProcesso")

                yield RawProperty(
                    external_code=lot_id or title[:30],
                    source_url=link,
                    bank_code="superleiloes",
                    source_name=_SOURCE_NAME,
                    raw_data={
                        "title": title,
                        "city": city,
                        "state": state,
                        "current_value": str(price) if price else None,
                        "appraisal_value": str(appraisal) if appraisal else None,
                        "auction_date": str(date) if date else None,
                        "official_url": link,
                        "process_number": process_num,
                    },
                )
            except Exception as exc:
                logger.warning("superleiloes.json_item_error", error=str(exc))
                continue

    def _parse_html(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        soup = BeautifulSoup(raw_bytes, "html.parser")
        items = (
            soup.select(".lote-card")
            or soup.select(".item-leilao")
            or soup.select("[data-lote-id]")
            or soup.select(".card-lote")
        )
        if not items:
            logger.debug("superleiloes.no_items", url=source_url)
            return

        for item in items:
            try:
                lot_id = item.get("data-lote-id") or item.get("id") or ""
                title = self._text(item, ["h2", "h3", ".lote-title", ".descricao", ".titulo"])
                city_state = self._text(item, [".localizacao", ".cidade", ".local"])
                city, state = self._split_city_state(city_state)
                price = self._text(item, [".lance-inicial", ".valor", ".preco"])
                link = self._href(item)

                yield RawProperty(
                    external_code=str(lot_id) or (title or "")[:30],
                    source_url=link or source_url,
                    bank_code="superleiloes",
                    source_name=_SOURCE_NAME,
                    raw_data={
                        "title": title,
                        "city": city,
                        "state": state,
                        "current_value": price,
                        "appraisal_value": None,
                        "auction_date": None,
                        "official_url": link or source_url,
                        "process_number": None,
                    },
                )
            except Exception as exc:
                logger.warning("superleiloes.html_item_error", error=str(exc))
                continue

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
        return href if href.startswith("http") else f"{_BASE_URL}{href}"

    @staticmethod
    def _split_city_state(text: str | None) -> tuple[str, str]:
        if not text:
            return "", "BR"
        parts = re.split(r"[/,\-–]", text.strip())
        city = parts[0].strip() if parts else ""
        state = parts[-1].strip().upper()[:2] if len(parts) > 1 else "BR"
        return city, state
