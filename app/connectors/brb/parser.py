"""Parser BRB — detecta fonte pela URL/conteúdo: Resale (JSON) ou oficial (HTML).

Defensivo: cada campo isolado; ausência gera logger.warning, nunca crash.
"""
import json
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.core.logging import logger

_CARD_SELECTORS = ["div.imovel", "article.imovel", "div.card-imovel", "li.imovel"]
_FIELD_SELECTORS = {
    "title": [".titulo", "h3", "h2", ".tipo"],
    "address": [".endereco", ".logradouro"],
    "neighborhood": [".bairro"],
    "city": [".cidade", ".municipio"],
    "state": [".uf", ".estado"],
    "current_value": [".valor", ".preco"],
    "appraisal_value": [".avaliacao"],
}

# Chaves prováveis no JSON da API Resale (hipótese).
_RESALE_KEYS = {
    "external_code": ("id", "codigo", "code", "imovelId"),
    "title": ("titulo", "descricao", "title", "nome"),
    "address": ("endereco", "logradouro", "address"),
    "neighborhood": ("bairro", "neighborhood"),
    "city": ("cidade", "municipio", "city"),
    "state": ("uf", "estado", "state"),
    "current_value": ("valor", "preco", "valorVenda", "price"),
    "appraisal_value": ("avaliacao", "valorAvaliacao"),
    "official_url": ("url", "link", "permalink"),
}


def _first_text(node, selectors: list[str]) -> str | None:
    for sel in selectors:
        try:
            found = node.select_one(sel)
        except Exception:
            found = None
        if found is not None:
            text = found.get_text(" ", strip=True)
            if text:
                return text
    return None


def _pick(item: dict, keys: tuple[str, ...]):
    for k in keys:
        if k in item and item[k] not in (None, ""):
            return item[k]
    return None


class BRBParser:
    BANK_CODE = "brb"

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            logger.warning("brb.parser.empty_bytes", source_url=source_url)
            return

        stripped = raw_bytes.lstrip()
        is_json = "resale" in source_url.lower() or stripped[:1] in (b"{", b"[")
        if is_json:
            yield from self._parse_json(raw_bytes, source_url)
        else:
            yield from self._parse_html(raw_bytes, source_url)

    def _parse_json(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        try:
            data = json.loads(raw_bytes.decode("utf-8", errors="replace"))
        except Exception as exc:
            logger.warning("brb.parser.json_failed", source_url=source_url, error=str(exc))
            return

        items = data
        if isinstance(data, dict):
            for key in ("imoveis", "items", "data", "results", "lista"):
                if isinstance(data.get(key), list):
                    items = data[key]
                    break
        if not isinstance(items, list):
            logger.warning("brb.parser.json_no_list", source_url=source_url)
            return

        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            try:
                raw_data = {
                    field: _pick(item, keys) for field, keys in _RESALE_KEYS.items()
                }
                external_code = str(raw_data.get("external_code") or f"brb-{idx}").strip()
                raw_data["external_code"] = external_code
                raw_data["official_url"] = raw_data.get("official_url") or source_url
                yield RawProperty(
                    external_code=external_code,
                    source_url=source_url,
                    raw_data=raw_data,
                    bank_code=self.BANK_CODE,
                    source_name="brb_resale",
                )
            except Exception as exc:
                logger.error("brb.parser.json_item_failed", index=idx, error=str(exc))

    def _parse_html(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        try:
            soup = BeautifulSoup(raw_bytes, "lxml")
        except Exception as exc:
            logger.error("brb.parser.soup_failed", source_url=source_url, error=str(exc))
            return

        cards: list = []
        for sel in _CARD_SELECTORS:
            cards = soup.select(sel)
            if cards:
                break
        if not cards:
            logger.warning("brb.parser.no_cards", source_url=source_url)
            return

        for idx, card in enumerate(cards):
            try:
                raw_data = {
                    field: _first_text(card, selectors)
                    for field, selectors in _FIELD_SELECTORS.items()
                }
                code_attr = card.get("data-codigo") if hasattr(card, "get") else None
                external_code = str(code_attr).strip() if code_attr else f"brb-{idx}"
                raw_data["external_code"] = external_code

                link = card.select_one("a[href]")
                href = link["href"].strip() if link and link.get("href") else source_url
                raw_data["official_url"] = href

                if not raw_data.get("city"):
                    logger.warning("brb.parser.field_missing", field="city", index=idx)

                yield RawProperty(
                    external_code=external_code,
                    source_url=source_url,
                    raw_data=raw_data,
                    bank_code=self.BANK_CODE,
                    source_name="brb_oficial",
                )
            except Exception as exc:
                logger.error("brb.parser.card_failed", index=idx, error=str(exc))
