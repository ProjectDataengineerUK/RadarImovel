"""Helpers de extração de PDF compartilhados (BNB, BASA, Banestes).

Defensivos: nunca levantam exceção; logam falhas e retornam listas vazias.
"""
import io

from app.core.logging import logger


def is_pdf(raw_bytes: bytes) -> bool:
    return bool(raw_bytes) and raw_bytes[:4] == b"%PDF"


def extract_tables(raw_bytes: bytes, source_url: str = "") -> list[list[list[str]]]:
    """Extrai todas as tabelas de um PDF como listas de linhas de células (str)."""
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdf.pdfplumber_not_installed", url=source_url)
        return []

    tables: list[list[list[str]]] = []
    try:
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            for page in pdf.pages:
                try:
                    for table in page.extract_tables() or []:
                        cleaned = [
                            [(cell or "").strip() for cell in row]
                            for row in table
                            if any(cell for cell in row)
                        ]
                        if cleaned:
                            tables.append(cleaned)
                except Exception as exc:
                    logger.warning("pdf.page_table_failed", url=source_url, error=str(exc))
    except Exception as exc:
        logger.error("pdf.parse_failed", url=source_url, error=str(exc))
    return tables


def extract_text(raw_bytes: bytes, source_url: str = "") -> str:
    """Extrai texto completo do PDF (fallback quando não há tabela estruturada)."""
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdf.pdfplumber_not_installed", url=source_url)
        return ""

    parts: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            for page in pdf.pages:
                try:
                    parts.append(page.extract_text() or "")
                except Exception as exc:
                    logger.warning("pdf.page_text_failed", url=source_url, error=str(exc))
    except Exception as exc:
        logger.error("pdf.text_failed", url=source_url, error=str(exc))
    return "\n".join(parts)


def rows_from_tables(
    tables: list[list[list[str]]],
) -> list[dict[str, str]]:
    """Converte tabelas (1a linha = header) em lista de dicts header→valor."""
    rows: list[dict[str, str]] = []
    for table in tables:
        if len(table) < 2:
            continue
        header = [h.lower().strip() for h in table[0]]
        for raw_row in table[1:]:
            if not any(raw_row):
                continue
            record = {}
            for i, cell in enumerate(raw_row):
                key = header[i] if i < len(header) and header[i] else f"col_{i}"
                record[key] = cell
            rows.append(record)
    return rows
