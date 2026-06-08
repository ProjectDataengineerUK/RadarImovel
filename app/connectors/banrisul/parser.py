"""Parser HTML Banrisul (cards ou tabela). Defensivo: nunca crash por campo."""
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.core.logging import logger

_CARD_SELECTORS = ["div.imovel", "div.card-imovel", "tr.imovel", "li.imovel", "div.bem"]
_FIELD_SELECTORS = {
    "title": [".titulo", ".tipo", "h3", "h2"],
    "address": [".endereco", ".logradouro"],
    "neighborhood": [".bairro"],
    "city": [".cidade", ".municipio"],
    "state": [".uf", ".estado"],
    "current_value": [".valor", ".preco"],
    "appraisal_value": [".avaliacao"],
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


class BanrisulParser:
    BANK_CODE = "banrisul"

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            logger.warning("banrisul.parser.empty_bytes", source_url=source_url)
            return
        try:
            soup = BeautifulSoup(raw_bytes, "lxml")
        except Exception as exc:
            logger.error("banrisul.parser.soup_failed", source_url=source_url, error=str(exc))
            return

        cards: list = []
        for sel in _CARD_SELECTORS:
            cards = soup.select(sel)
            if cards:
                break
        if not cards:
            logger.warning("banrisul.parser.no_cards", source_url=source_url)
            return

        for idx, card in enumerate(cards):
            try:
                raw_data = {
                    field: _first_text(card, selectors)
                    for field, selectors in _FIELD_SELECTORS.items()
                }
                code_attr = card.get("data-codigo") if hasattr(card, "get") else None
                external_code = str(code_attr).strip() if code_attr else f"banrisul-{idx}"
                raw_data["external_code"] = external_code
                link = card.select_one("a[href]")
                raw_data["official_url"] = (
                    link["href"].strip() if link and link.get("href") else source_url
                )
                if not raw_data.get("city"):
                    logger.warning("banrisul.parser.field_missing", field="city", index=idx)
                yield RawProperty(
                    external_code=external_code,
                    source_url=source_url,
                    raw_data=raw_data,
                    bank_code=self.BANK_CODE,
                    source_name="banrisul_html",
                )
            except Exception as exc:
                logger.error("banrisul.parser.card_failed", index=idx, error=str(exc))
