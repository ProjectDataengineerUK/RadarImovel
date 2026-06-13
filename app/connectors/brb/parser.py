"""Parser BRB — Resale SPA (feiraobrb.com.br) renderizada via Playwright.

CSS module classes reais (de feiraobrb.com.br/static/css/main.8b8ff469.chunk.css):
  PropertyCard_card__34IZS    — container do card
  PropertyCard_link__2x6xY    — link (href="/imovel/ID")
  PropertyCard_propertyTitle__11JKm — título
  PropertyCard_resumeAddress__3epIV — endereço / localização
  PropertyCard_prices__rdto_   — seção de preços
  PropertyCard_values__1BhDP   — valor(es) dentro de prices
  PropertyCard_tags__x6cOC     — tags (Venda direta, Leilão…)

O hash no sufixo (__34IZS etc.) muda entre builds: usamos class*= para ser resiliente.
"""
import re
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.core.logging import logger

_BASE_URL = "https://feiraobrb.com.br"
# "Taguatinga Norte, Brasília - DF" → city="Taguatinga Norte, Brasília", state="DF"
_ADDR_STATE_RE = re.compile(r"-\s*([A-Z]{2})\s*$")


def _css_module(tag, prefix: str):
    """First child/descendant with a class matching prefix (class*=prefix)."""
    return tag.find(class_=re.compile(re.escape(prefix)))


def _text(el) -> str:
    return el.get_text(strip=True) if el else ""


class BRBParser:
    BANK_CODE = "brb"

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            logger.warning("brb.parser.empty_bytes", source_url=source_url)
            return
        try:
            soup = BeautifulSoup(raw_bytes, "lxml")
        except Exception as exc:
            logger.error("brb.parser.soup_failed", source_url=source_url, error=str(exc))
            return

        cards = soup.find_all(class_=re.compile(r"PropertyCard_card"))
        if not cards:
            logger.warning("brb.parser.no_cards", source_url=source_url, hint="[class*=PropertyCard_card]")
            return

        found = 0
        for idx, card in enumerate(cards):
            try:
                link_el = _css_module(card, "PropertyCard_link") or _css_module(card, "PropertyCard_imageLink")
                if link_el is None:
                    continue
                href = str(link_el.get("href", "")).strip()
                external_code = href.rstrip("/").split("/")[-1] or f"brb-{idx}"
                official_url = href if href.startswith("http") else _BASE_URL + href

                title = _text(_css_module(card, "PropertyCard_propertyTitle"))
                address = _text(_css_module(card, "PropertyCard_resumeAddress"))
                valor = _text(_css_module(card, "PropertyCard_values"))

                state = ""
                m = _ADDR_STATE_RE.search(address)
                if m:
                    state = m.group(1)

                tags_el = _css_module(card, "PropertyCard_tags")
                tags_text = _text(tags_el)
                if "Leilão" in tags_text or "leilao" in tags_text.lower():
                    modality = "Leilão"
                else:
                    modality = "Venda direta"

                raw_data = {
                    "external_code": external_code,
                    "title": title,
                    "address": address,
                    "state": state,
                    "current_value": valor,
                    "sale_modality": modality,
                    "official_url": official_url,
                }

                yield RawProperty(
                    external_code=external_code,
                    source_url=source_url,
                    raw_data=raw_data,
                    bank_code=self.BANK_CODE,
                    source_name="brb_resale",
                )
                found += 1
            except Exception as exc:
                logger.error("brb.parser.card_failed", index=idx, error=str(exc))

        if found == 0:
            logger.warning("brb.parser.no_listings", source_url=source_url)
        else:
            logger.info("brb.parser.done", count=found, source_url=source_url)
