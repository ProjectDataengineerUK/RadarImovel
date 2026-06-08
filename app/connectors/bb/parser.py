"""Parser HTML do portal de imóveis do Banco do Brasil.

Defensivo: cada campo em try/except; campos ausentes geram logger.warning e
seguem como None. Nunca crash por campo faltando.
"""
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.core.logging import logger

# Seletores são hipóteses; ajustáveis sem tocar no resto do connector.
_CARD_SELECTORS = ["div.imovel", "div.card-imovel", "tr.imovel", "li.imovel"]
_FIELD_SELECTORS = {
    "external_code": ["[data-codigo]", ".codigo", ".cod-imovel"],
    "title": [".titulo", ".tipo-imovel", "h3", "h2"],
    "address": [".endereco", ".logradouro"],
    "neighborhood": [".bairro"],
    "city": [".cidade", ".municipio"],
    "state": [".uf", ".estado"],
    "current_value": [".valor", ".preco", ".valor-venda"],
    "appraisal_value": [".avaliacao", ".valor-avaliacao"],
    "discount_percent": [".desconto"],
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


def _find_cards(soup: BeautifulSoup) -> list:
    for sel in _CARD_SELECTORS:
        cards = soup.select(sel)
        if cards:
            return cards
    return []


def _extract_url(node, base_url: str) -> str | None:
    try:
        link = node.select_one("a[href]")
        if link and link.get("href"):
            href = str(link["href"]).strip()
            if href.startswith("http"):
                return href
            return base_url.rsplit("/", 1)[0] + "/" + href.lstrip("/")
    except Exception:
        return None
    return None


class BBParser:
    BANK_CODE = "bb"

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            logger.warning("bb.parser.empty_bytes", source_url=source_url)
            return
        try:
            soup = BeautifulSoup(raw_bytes, "lxml")
        except Exception as exc:
            logger.error("bb.parser.soup_failed", source_url=source_url, error=str(exc))
            return

        cards = _find_cards(soup)
        if not cards:
            logger.warning("bb.parser.no_cards", source_url=source_url)
            return

        for idx, card in enumerate(cards):
            try:
                raw_data: dict = {}
                for field, selectors in _FIELD_SELECTORS.items():
                    value = _first_text(card, selectors)
                    if value is None and field in ("external_code", "city"):
                        logger.warning("bb.parser.field_missing", field=field, index=idx)
                    raw_data[field] = value

                external_code = (raw_data.get("external_code") or "").strip()
                if not external_code:
                    code_attr = card.get("data-codigo") if hasattr(card, "get") else None
                    external_code = str(code_attr).strip() if code_attr else f"bb-{idx}"

                raw_data["external_code"] = external_code
                raw_data["official_url"] = _extract_url(card, source_url) or source_url

                yield RawProperty(
                    external_code=external_code,
                    source_url=source_url,
                    raw_data=raw_data,
                    bank_code=self.BANK_CODE,
                    source_name="bb_portal",
                )
            except Exception as exc:
                logger.error("bb.parser.card_failed", index=idx, error=str(exc))
