"""DataJud/CNJ — busca de hastas públicas e leilões judiciais por endereço/coordenadas.

Complementa cnj.py (processos genéricos) com foco em hasta pública e penhora
ativa — útil para a dimensão jurídica do risco de imóveis de leiloeiros.
"""
import unicodedata

import httpx

from app.core.logging import logger

_BASE = "https://api-publica.datajud.cnj.jus.br"
_HASTA_KEYWORDS = {"hasta", "leilao", "arrematacao", "penhora", "adjudicacao"}
_TIMEOUT = 15


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

    @staticmethod
    def _fmt(src: dict) -> dict:
        return {
            "numero": src.get("numeroProcesso", ""),
            "classe": src.get("classe", {}).get("nome", ""),
            "tribunal": src.get("tribunal", ""),
            "status": "ativo" if src.get("movimentos") else "arquivado",
        }
