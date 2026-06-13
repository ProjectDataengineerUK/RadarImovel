"""Parser BNB — PDF de relação de bens à venda (pdfplumber).

Real PDF headers: LOTE | DESCRIÇÃO DO LOTE | VALOR\nMÍNIMO (R$)
City/state are embedded in the description: "CEARÁ- CRATO-CE (AG. CRATO-CE) ..."
"""
import re
from collections.abc import Iterator

from app.connectors.base import RawProperty
from app.connectors.pdf_utils import extract_tables, is_pdf, rows_from_tables
from app.core.logging import logger

# Pairs of (field, pattern) — first match wins; patterns use word boundaries
_COLUMN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # More-specific patterns first to avoid "lote" matching "descrição do lote"
    ("external_code", re.compile(r"^(lote|item|c[oó]digo|n[oº]|matr[ií]cula)$")),
    ("title", re.compile(r"descri[çc][aã]o|im[oó]vel|tipo|bem")),
    ("current_value", re.compile(r"valor|pre[çc]o|lance|m[ií]nimo")),
]

# "CEARÁ- CRATO-CE (AG. ..." → state=CE, city=CRATO
_LOCATION_RE = re.compile(
    r"^[A-ZÁÉÍÓÚÃÕÂÊÎÔÛ\s]+-\s*([\w\sÀ-ú]+?)-([A-Z]{2})[\s\(]",
    re.IGNORECASE,
)
# "Localização: Rua X, nº 123, Bairro Y, em CIDADE/UF."
_LOC_ALT_RE = re.compile(r"em\s+([\w\sÀ-ú]+)[/-]([A-Z]{2})[\s\.]", re.IGNORECASE)


def _match_field(header: str) -> str | None:
    h = header.lower().strip()
    for field, pattern in _COLUMN_PATTERNS:
        if pattern.search(h):
            return field
    return None


def _remap_record(record: dict[str, str]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for key, value in record.items():
        field = _match_field(key)
        if field and field not in out:
            out[field] = value
    return out


def _extract_location(description: str) -> tuple[str | None, str | None]:
    m = _LOCATION_RE.match(description.strip())
    if m:
        return m.group(1).strip().title(), m.group(2).upper()
    m2 = _LOC_ALT_RE.search(description)
    if m2:
        return m2.group(1).strip().title(), m2.group(2).upper()
    return None, None


class BNBParser:
    BANK_CODE = "bnb"

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            logger.warning("bnb.parser.empty_bytes", source_url=source_url)
            return
        if not is_pdf(raw_bytes):
            logger.warning("bnb.parser.not_pdf", source_url=source_url)
            return
        yield from self._parse_pdf(raw_bytes, source_url)

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

                description = remapped.get("title") or ""
                city, state = _extract_location(description)

                external_code = (remapped.get("external_code") or f"bnb-{idx}").strip()
                remapped["external_code"] = external_code
                remapped["city"] = city
                remapped["state"] = state
                remapped["official_url"] = source_url
                remapped["edital_url"] = source_url

                yield RawProperty(
                    external_code=external_code,
                    source_url=source_url,
                    raw_data=remapped,
                    bank_code=self.BANK_CODE,
                    source_name="bnb_relacao_pdf",
                )
            except Exception as exc:
                logger.error("bnb.parser.pdf_row_failed", index=idx, error=str(exc))
