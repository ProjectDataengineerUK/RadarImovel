"""Parser BNB — HTML da página "Bens à Venda" ou PDF de relação (pdfplumber).

Defensivo: cada linha/campo isolado; ausência gera logger.warning, nunca crash.
"""
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.connectors.pdf_utils import extract_tables, is_pdf, rows_from_tables
from app.core.logging import logger

# Mapeia possíveis cabeçalhos de coluna do PDF/tabela → campos internos.
_COLUMN_ALIASES = {
    "external_code": ("item", "código", "codigo", "nº", "no", "matrícula", "matricula"),
    "title": ("descrição", "descricao", "imóvel", "imovel", "tipo", "bem"),
    "address": ("endereço", "endereco", "localização", "localizacao"),
    "city": ("município", "municipio", "cidade", "comarca"),
    "state": ("uf", "estado"),
    "appraisal_value": ("avaliação", "avaliacao", "valor de avaliação", "valor avaliacao"),
    "current_value": ("valor", "preço", "preco", "valor mínimo", "valor minimo", "lance"),
}


def _match_field(header: str) -> str | None:
    h = header.lower().strip()
    for field, aliases in _COLUMN_ALIASES.items():
        if any(alias in h for alias in aliases):
            return field
    return None


def _remap_record(record: dict[str, str]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for key, value in record.items():
        field = _match_field(key)
        if field and field not in out:
            out[field] = value
    return out


class BNBParser:
    BANK_CODE = "bnb"

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            logger.warning("bnb.parser.empty_bytes", source_url=source_url)
            return
        if is_pdf(raw_bytes):
            yield from self._parse_pdf(raw_bytes, source_url)
        else:
            yield from self._parse_html(raw_bytes, source_url)

    def _parse_pdf(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        tables = extract_tables(raw_bytes, source_url)
        if not tables:
            logger.warning("bnb.parser.pdf_no_tables", source_url=source_url)
            return
        for idx, record in enumerate(rows_from_tables(tables)):
            try:
                remapped = _remap_record(record)
                if not any(remapped.values()):
                    continue
                external_code = (remapped.get("external_code") or f"bnb-{idx}").strip()
                remapped["external_code"] = external_code
                remapped["official_url"] = source_url
                remapped["edital_url"] = source_url if source_url.lower().endswith(".pdf") else None
                yield RawProperty(
                    external_code=external_code,
                    source_url=source_url,
                    raw_data=remapped,
                    bank_code=self.BANK_CODE,
                    source_name="bnb_relacao_pdf",
                )
            except Exception as exc:
                logger.error("bnb.parser.pdf_row_failed", index=idx, error=str(exc))

    def _parse_html(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        try:
            soup = BeautifulSoup(raw_bytes, "lxml")
        except Exception as exc:
            logger.error("bnb.parser.soup_failed", source_url=source_url, error=str(exc))
            return

        rows = soup.select("table tr")
        data_rows = [r for r in rows if r.find_all("td")]
        if not data_rows:
            logger.warning("bnb.parser.no_rows", source_url=source_url)
            return

        headers = [th.get_text(strip=True) for th in soup.select("table tr th")]
        for idx, row in enumerate(data_rows):
            try:
                cells = [td.get_text(" ", strip=True) for td in row.find_all("td")]
                record = {}
                for i, cell in enumerate(cells):
                    key = headers[i] if i < len(headers) and headers[i] else f"col_{i}"
                    record[key] = cell
                remapped = _remap_record(record)
                external_code = (remapped.get("external_code") or f"bnb-{idx}").strip()
                remapped["external_code"] = external_code
                link = row.select_one("a[href]")
                href = link.get("href") if link else None
                remapped["official_url"] = str(href).strip() if href else source_url
                if not remapped.get("city"):
                    logger.warning("bnb.parser.field_missing", field="city", index=idx)
                yield RawProperty(
                    external_code=external_code,
                    source_url=source_url,
                    raw_data=remapped,
                    bank_code=self.BANK_CODE,
                    source_name="bnb_html",
                )
            except Exception as exc:
                logger.error("bnb.parser.row_failed", index=idx, error=str(exc))
