"""Parser Banestes — HTML índice de editais ou PDF de edital (pdfplumber).

Defensivo: cada linha/campo isolado; ausência gera logger.warning, nunca crash.
"""
import re
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.connectors.pdf_utils import extract_tables, extract_text, is_pdf, rows_from_tables
from app.core.logging import logger

_COLUMN_ALIASES = {
    "external_code": ("item", "lote", "nº", "no", "código", "codigo"),
    "title": ("descrição", "descricao", "imóvel", "imovel", "bem", "tipo"),
    "address": ("endereço", "endereco", "localização", "localizacao"),
    "city": ("município", "municipio", "cidade", "comarca"),
    "state": ("uf", "estado"),
    "appraisal_value": ("avaliação", "avaliacao"),
    "current_value": ("lance", "valor", "preço", "preco", "mínimo", "minimo"),
}

_EDITAL_RE = re.compile(r"edital[\s\w]*?n[ºo°.]?\s*([\w./-]+)", re.IGNORECASE)
_DATE_RE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b")


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


class BanestesParser:
    BANK_CODE = "banestes"

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            logger.warning("banestes.parser.empty_bytes", source_url=source_url)
            return
        if is_pdf(raw_bytes):
            yield from self._parse_pdf(raw_bytes, source_url)
        else:
            self._log_index(raw_bytes, source_url)

    def _log_index(self, raw_bytes: bytes, source_url: str) -> None:
        try:
            soup = BeautifulSoup(raw_bytes, "lxml")
            pdfs = [
                a.get("href")
                for a in soup.select("a[href]")
                if re.search(r"\.pdf", str(a.get("href", "")), re.IGNORECASE)
            ]
            logger.info("banestes.parser.index_only", source_url=source_url, pdf_links=len(pdfs))
        except Exception as exc:
            logger.error("banestes.parser.index_failed", source_url=source_url, error=str(exc))

    def _parse_pdf(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        text = extract_text(raw_bytes, source_url)
        edital_number = None
        auction_date = None
        m = _EDITAL_RE.search(text)
        if m:
            edital_number = m.group(1).strip()
        dm = _DATE_RE.search(text)
        if dm:
            auction_date = dm.group(1)

        tables = extract_tables(raw_bytes, source_url)
        if not tables:
            logger.warning("banestes.parser.pdf_no_tables", source_url=source_url)
            return
        for idx, record in enumerate(rows_from_tables(tables)):
            try:
                remapped = _remap(record)
                if not any(remapped.values()):
                    continue
                external_code = (remapped.get("external_code") or f"banestes-{idx}").strip()
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
                    source_name="banestes_edital_pdf",
                )
            except Exception as exc:
                logger.error("banestes.parser.pdf_row_failed", index=idx, error=str(exc))
