"""Parser BASA — HTML SSR da tabela de leilões ou PDF de edital.

Real SSR table columns: Comarca/Nº Processo | Praça/Data/Horário | Leiloeiro |
Cidade/Estado | Edital (link PDF via a.rich-text-link).
Cidade/Estado format: "Ananindeu/PA" → city=Ananindeu, state=PA.
"""
import re
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.connectors.pdf_utils import extract_tables, extract_text, is_pdf, rows_from_tables
from app.core.logging import logger

_DATE_RE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b")
_EDITAL_RE = re.compile(r"edital[\s\w]*?n[ºo°.]?\s*([\w./-]+)", re.IGNORECASE)

# "Ananindeu/PA" or "Rio de Janeiro/RJ"
_CITY_STATE_RE = re.compile(r"^([\w\s\xa0À-ú]+?)/([A-Z]{2})$", re.IGNORECASE)

# PDF column aliases (fallback when BASA eventually publishes PDFs with tables)
_COLUMN_ALIASES = {
    "external_code": ("lote", "item", "nº", "no", "código", "codigo"),
    "title": ("descrição", "descricao", "imóvel", "imovel", "bem", "tipo"),
    "address": ("endereço", "endereco", "localização", "localizacao"),
    "city": ("município", "municipio", "cidade", "comarca"),
    "state": ("uf", "estado"),
    "appraisal_value": ("avaliação", "avaliacao"),
    "current_value": ("lance", "valor", "preço", "preco", "mínimo", "minimo"),
}


def _match_field(header: str) -> str | None:
    h = header.lower().strip()
    for field, aliases in _COLUMN_ALIASES.items():
        if any(alias in h for alias in aliases):
            return field
    return None


def _remap(record: dict[str, str]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for key, value in record.items():
        field = _match_field(key)
        if field and field not in out:
            out[field] = value
    return out


def _parse_city_state(text: str) -> tuple[str | None, str | None]:
    text = text.strip().replace("\xa0", " ")
    m = _CITY_STATE_RE.match(text)
    if m:
        return m.group(1).strip().title(), m.group(2).upper()
    return None, None


class BASAParser:
    BANK_CODE = "basa"

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            logger.warning("basa.parser.empty_bytes", source_url=source_url)
            return
        if is_pdf(raw_bytes):
            yield from self._parse_pdf(raw_bytes, source_url)
        else:
            yield from self._parse_index(raw_bytes, source_url)

    def _parse_index(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        try:
            soup = BeautifulSoup(raw_bytes, "lxml")
        except Exception as exc:
            logger.error("basa.parser.soup_failed", source_url=source_url, error=str(exc))
            return

        table = soup.find("table")
        if not table:
            logger.warning("basa.parser.no_table", source_url=source_url)
            return

        rows = table.find_all("tr")
        data_rows = rows[1:]  # skip header row
        if not data_rows:
            logger.info("basa.parser.no_listings", source_url=source_url)
            return

        for idx, row in enumerate(data_rows):
            try:
                cells = row.find_all(["td", "th"])
                if len(cells) < 4:
                    continue

                comarca_text = cells[0].get_text(" ", strip=True).replace("\xa0", " ")
                datas_text = cells[1].get_text(" ", strip=True) if len(cells) > 1 else ""
                leiloeiro = cells[2].get_text(" ", strip=True) if len(cells) > 2 else ""
                cidade_estado = cells[3].get_text(" ", strip=True) if len(cells) > 3 else ""

                # PDF edital link in last cell
                edital_url: str | None = None
                if len(cells) > 4:
                    link = cells[4].find("a", href=True)
                    if link:
                        edital_url = str(link["href"]).strip()

                city, state = _parse_city_state(cidade_estado)

                # Extract first auction date from datas_text
                dm = _DATE_RE.search(datas_text)
                auction_date = dm.group(1) if dm else None

                external_code = (
                    re.sub(r"\s+", "_", comarca_text[:80]).strip("_") or f"basa-{idx}"
                )

                raw_data: dict = {
                    "external_code": external_code,
                    "title": f"Leilão BASA — {comarca_text}",
                    "city": city,
                    "state": state,
                    "auction_date": auction_date,
                    "sale_modality": "Leilão",
                    "auctioneer": leiloeiro,
                    "praça_info": datas_text,
                    "comarca": comarca_text,
                    "edital_url": edital_url,
                    "official_url": edital_url or source_url,
                }

                yield RawProperty(
                    external_code=external_code,
                    source_url=source_url,
                    raw_data=raw_data,
                    bank_code=self.BANK_CODE,
                    source_name="basa_html_table",
                )
            except Exception as exc:
                logger.error("basa.parser.row_failed", index=idx, error=str(exc))

    def _parse_pdf(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        text = extract_text(raw_bytes, source_url)
        edital_number: str | None = None
        auction_date: str | None = None
        m = _EDITAL_RE.search(text)
        if m:
            edital_number = m.group(1).strip()
        dm = _DATE_RE.search(text)
        if dm:
            auction_date = dm.group(1)

        tables = extract_tables(raw_bytes, source_url)
        if not tables:
            logger.warning("basa.parser.pdf_no_tables", source_url=source_url)
            return

        for idx, record in enumerate(rows_from_tables(tables)):
            try:
                remapped = _remap(record)
                if not any(remapped.values()):
                    continue
                external_code = (remapped.get("external_code") or f"basa-{idx}").strip()
                remapped["external_code"] = external_code
                remapped["edital_number"] = edital_number
                remapped["auction_date"] = auction_date
                remapped["edital_url"] = source_url
                remapped["official_url"] = source_url
                yield RawProperty(
                    external_code=external_code,
                    source_url=source_url,
                    raw_data=remapped,
                    bank_code=self.BANK_CODE,
                    source_name="basa_edital_pdf",
                )
            except Exception as exc:
                logger.error("basa.parser.pdf_row_failed", index=idx, error=str(exc))
