"""DataJud/CNJ — busca de hastas públicas e leilões judiciais por endereço/coordenadas.

Complementa cnj.py (processos genéricos) com foco em hasta pública e penhora
ativa — útil para a dimensão jurídica do risco de imóveis de leiloeiros.
"""
import unicodedata
from datetime import UTC, datetime, timedelta

import httpx

from app.core.logging import logger

_BASE = "https://api-publica.datajud.cnj.jus.br"
_HASTA_KEYWORDS = {"hasta", "leilao", "arrematacao", "penhora", "adjudicacao"}
_TIMEOUT = 15

TRIBUNAL_CODES: dict[str, str] = {
    "TRT1": "trt-1",
    "TRT2": "trt-2",
    "TRT3": "trt-3",
    "TRT4": "trt-4",
    "TRT5": "trt-5",
    "TRT15": "trt-15",
    "TRF1": "trf-1",
    "TRF2": "trf-2",
    "TRF3": "trf-3",
    "TRF4": "trf-4",
    "TRF5": "trf-5",
    "TJSP": "tjsp",
    "TJRJ": "tjrj",
    "TJMG": "tjmg",
    "TJRS": "tjrs",
    "TJPR": "tjpr",
    "TJSC": "tjsc",
    "TJBA": "tjba",
    "TJPE": "tjpe",
    "TJCE": "tjce",
    "TJGO": "tjgo",
    "TJDF": "tjdft",
    "TJMT": "tjmt",
    "TJPA": "tjpa",
}

HASTA_CLASS_CODES = [
    "Arrematação",
    "Hasta Pública",
    "Leilão",
    "Adjudicação",
    "Alienação Judicial",
]


def _norm(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()


class DataJudClient:
    """Consulta DataJud por hastas públicas ligadas a um endereço/imóvel."""

    def __init__(self, timeout: int = _TIMEOUT) -> None:
        self._timeout = timeout

    def search_hasta(
        self,
        *,
        address: str = "",
        city: str = "",
        state: str = "",
        cnpj: str | None = None,
    ) -> list[dict]:
        """Retorna processos de hasta pública / penhora relacionados ao imóvel."""
        results: list[dict] = []

        if cnpj:
            results = self._by_document(cnpj)
            if results:
                return results

        query = " ".join(filter(None, [address, city, state]))
        if query:
            results = self._by_query(query)

        return results

    def _by_document(self, doc: str) -> list[dict]:
        doc_clean = "".join(c for c in doc if c.isdigit())
        try:
            resp = httpx.get(
                f"{_BASE}/api_publica/processo",
                params={"numeroDocumento": doc_clean, "size": 20},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
            return [self._fmt(h["_source"]) for h in hits if self._is_hasta(h)]
        except Exception as exc:
            logger.warning("datajud.by_document_failed", doc=doc_clean[:4] + "****", error=str(exc))
            return []

    def _by_query(self, query: str) -> list[dict]:
        try:
            resp = httpx.get(
                f"{_BASE}/api_publica/processo",
                params={"query": query, "size": 10},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
            return [self._fmt(h["_source"]) for h in hits if self._is_hasta(h)]
        except Exception as exc:
            logger.warning("datajud.by_query_failed", query=query[:40], error=str(exc))
            return []

    @staticmethod
    def _is_hasta(hit: dict) -> bool:
        src = hit.get("_source", {})
        classe_raw = src.get("classe", {}).get("nome", "")
        return any(kw in _norm(classe_raw) for kw in _HASTA_KEYWORDS)

    def search_hastas_tribunal(
        self,
        *,
        tribunal: str,
        days_back: int = 30,
        page: int = 0,
        size: int = 50,
    ) -> list[dict]:
        """Busca hastas públicas de imóveis em um tribunal específico via DataJud."""
        index = TRIBUNAL_CODES.get(tribunal.upper(), tribunal.lower())
        since = (datetime.now(UTC) - timedelta(days=days_back)).strftime("%Y-%m-%d")
        try:
            resp = httpx.get(
                f"{_BASE}/api_publica/{index}",
                params={
                    "query": "hasta pública imóvel",
                    "dataInicio": since,
                    "size": size,
                    "from": page * size,
                    "classe": ",".join(HASTA_CLASS_CODES),
                },
                timeout=self._timeout,
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
            return [self._fmt_hasta(h.get("_source", h)) for h in hits]
        except Exception as exc:
            logger.warning(
                "datajud.search_tribunal_failed", tribunal=tribunal, page=page, error=str(exc)
            )
            return []

    @staticmethod
    def _fmt_hasta(src: dict) -> dict:
        movimentos = src.get("movimentos", [])
        hasta_mov = next(
            (m for m in movimentos if "hasta" in m.get("nome", "").lower() or "leil" in m.get("nome", "").lower()),
            None,
        )
        return {
            "process_number": src.get("numeroProcesso", ""),
            "summary": src.get("classe", {}).get("nome", ""),
            "tribunal": src.get("tribunal", ""),
            "city": src.get("orgaoJulgador", {}).get("municipioNome", ""),
            "state": src.get("orgaoJulgador", {}).get("estadoAbreviacao", ""),
            "hasta_date": hasta_mov.get("dataHora") if hasta_mov else None,
            "minimum_value": None,
            "auctioneer": None,
            "process_url": f"https://www.cnj.jus.br/pjecnj/consulta-publica#{src.get('numeroProcesso', '')}",
        }

    @staticmethod
    def _fmt(src: dict) -> dict:
        return {
            "numero": src.get("numeroProcesso", ""),
            "classe": src.get("classe", {}).get("nome", ""),
            "tribunal": src.get("tribunal", ""),
            "status": "ativo" if src.get("movimentos") else "arquivado",
        }
