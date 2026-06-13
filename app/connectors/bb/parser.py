"""Parser seuimovelbb.com.br — página inicial SSR com cards div.card.carta.

Estrutura real do card:
  <div class="card carta">
    <a href="/imovel/id/10050">...</a>          — link do imóvel
    <div class="tipo"><i>...</i> Prédio</div>   — tipo
    <div class="valor">R$ 31.956.084,00</div>   — valor
    <div class="localidade"><i>...</i> Rio de Janeiro, RJ</div>
    <div class="leilao [d-none hidden]">Leilão - ID 74833</div>
    <div class="leilao [d-none hidden]">Terça, 23/06 às 11h</div>
    <div class="leilao [d-none hidden]">Venda direta - ID 74833</div>
    <i onclick="_compartilhar('ID74833 ...', 'http://seuimovelbb.com.br/imovel/id/10050');"></i>
    <div class="parceiro">Parceiro: Escritório de Leilões</div>
  </div>

O BB ID real (ex: "74833") está no onclick de _compartilhar: match ID seguido de digitos.
"""
import re
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.core.logging import logger

_BASE_URL = "https://seuimovelbb.com.br"
_BB_ID_RE = re.compile(r"_compartilhar\('ID(\d+)", re.IGNORECASE)
_CITY_STATE_RE = re.compile(r"^(.+),\s*([A-Z]{2})$")


def _visible(tag) -> bool:
    classes = tag.get("class", [])
    return "d-none" not in classes and "hidden" not in classes


def _text(tag, selector: str) -> str:
    el = tag.select_one(selector)
    return el.get_text(strip=True) if el else ""


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

        cards = soup.find_all("div", class_=["card", "carta"])
        if not cards:
            logger.warning("bb.parser.no_cards", source_url=source_url, hint="div.card.carta")
            return

        found = 0
        for idx, card in enumerate(cards):
            try:
                link = card.find("a", href=lambda h: h and "/imovel/id/" in h)
                if not link:
                    continue
                href = str(link["href"]).strip()
                website_id = href.rstrip("/").split("/")[-1]
                official_url = _BASE_URL + href

                # BB internal ID from the compartilhar onclick
                share_el = card.find("i", onclick=True)
                onclick = str(share_el.get("onclick", "")) if share_el else ""
                m = _BB_ID_RE.search(onclick)
                external_code = m.group(1) if m else website_id

                tipo = _text(card, "div.tipo")
                valor = _text(card, "div.valor")
                localidade = _text(card, "div.localidade")

                city = state = ""
                loc_m = _CITY_STATE_RE.match(localidade)
                if loc_m:
                    city = loc_m.group(1).strip()
                    state = loc_m.group(2).strip()

                sale_modality = ""
                auction_date = ""
                for ld in card.find_all("div", class_="leilao"):
                    if not _visible(ld):
                        continue
                    text = ld.get_text(" ", strip=True)
                    if "Leil" in text:
                        sale_modality = "Leilão"
                    elif "Venda direta" in text:
                        sale_modality = "Venda direta"
                    elif text:
                        auction_date = text

                parceiro = _text(card, "div.parceiro").removeprefix("Parceiro:").strip()

                raw_data = {
                    "external_code": external_code,
                    "website_id": website_id,
                    "title": tipo,
                    "current_value": valor,
                    "city": city,
                    "state": state,
                    "sale_modality": sale_modality or "Venda direta",
                    "auction_date": auction_date,
                    "partner": parceiro,
                    "official_url": official_url,
                }

                yield RawProperty(
                    external_code=external_code,
                    source_url=source_url,
                    raw_data=raw_data,
                    bank_code=self.BANK_CODE,
                    source_name="bb_seuimovelbb",
                )
                found += 1
            except Exception as exc:
                logger.error("bb.parser.card_failed", index=idx, error=str(exc))

        if found == 0:
            logger.warning("bb.parser.no_listings", source_url=source_url)
        else:
            logger.info("bb.parser.done", count=found, source_url=source_url)
