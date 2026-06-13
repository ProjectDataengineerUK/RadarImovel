"""Parser HTML do Fidalgo Leilões (fidalgoleiloes.com.br).

Cada página de leilão (/leilao.php?idLeilao=N) contém lotes .lotePadrao.
O lot ID está no atributo onclick da div: goTo('lote.php?idLote=82691').
Lotes com classe .loteRetirado são ignorados.
"""
import re
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.core.logging import logger

_BASE_URL = "https://www.fidalgoleiloes.com.br"
_SOURCE_NAME = "fidalgo_imoveis"


class FidalgoParser:
    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            return
        soup = BeautifulSoup(raw_bytes, "html.parser")
        lots = soup.select(".lotePadrao")
        if not lots:
            logger.warning("fidalgo.parser.no_cards", url=source_url)
            return
        for lot in lots:
            if "loteRetirado" in (lot.get("class") or []):
                continue
            try:
                yield from self._parse_lot(lot, source_url)
            except Exception as exc:
                logger.warning("fidalgo.parser.card_error", error=str(exc))

    def _parse_lot(self, lot, source_url: str) -> Iterator[RawProperty]:
        # Lot ID from onclick="goTo('lote.php?idLote=82691')"
        onclick_div = lot.find(attrs={"onclick": re.compile(r"goTo\('lote\.php")})
        if not onclick_div:
            return
        onclick_val = str(onclick_div.get("onclick", ""))
        lot_id_match = re.search(r"idLote=(\d+)", onclick_val)
        if not lot_id_match:
            return
        lot_id = lot_id_match.group(1)
        url = f"{_BASE_URL}/lote.php?idLote={lot_id}"

        # Remove modal HTML to get clean text
        for modal in lot.select(".modal"):
            modal.decompose()

        # Title/description from .lotePadraoBens div:first-child
        bens_el = lot.select_one(".lotePadraoBens div")
        title = bens_el.get_text(strip=True) if bens_el else None

        # Address from .lotePadraoBens .mt-2
        addr_els = lot.select(".lotePadraoBens .mt-2")
        address = addr_els[0].get_text(strip=True) if addr_els else None
        if address:
            address = re.sub(r"^Local do bem:\s*", "", address, flags=re.I)

        # Current bid from .lotePadraoLanceInicial
        price_el = lot.select_one(".lotePadraoLanceInicial")
        current_value = None
        if price_el:
            price_match = re.search(r"R\$\s*([\d.,]+)", price_el.get_text())
            current_value = f"R$ {price_match.group(1)}" if price_match else None

        # Auction status
        status_el = lot.select_one(".lotePadraoStatus")
        sale_modality = status_el.get_text(strip=True) if status_el else None

        img_tag = lot.select_one("img[src]")
        photo = img_tag["src"] if img_tag else None
        if photo and not photo.startswith("http"):
            photo = f"{_BASE_URL}/{photo.lstrip('/')}"

        yield RawProperty(
            external_code=lot_id,
            source_url=url,
            bank_code="fidalgo",
            source_name=_SOURCE_NAME,
            raw_data={
                "external_code": lot_id,
                "title": title,
                "address": address,
                "current_value": current_value,
                "sale_modality": sale_modality,
                "official_url": url,
                "photo_url": photo,
            },
        )
