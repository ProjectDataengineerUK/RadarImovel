"""CNJ Datajud REST client — busca por CPF/CNPJ e por endereço (fallback)."""
import unicodedata

import httpx

_BASE = "https://api-publica.datajud.cnj.jus.br"
# Keywords normalized (no accent, no space/underscore) — matched against normalized class name
_CLASSES_IMOVEIS_KEYWORDS = {
    "execucao",
    "inventar",
    "usucapiao",
    "reintegracao",
    "despejo",
    "arresto",
    "penhora",
}


def _norm(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()


class CnjClient:
    def __init__(self, timeout: int = 15) -> None:
        self._timeout = timeout

    def search(
        self,
        *,
        cnpj: str | None = None,
        address: str = "",
        city: str = "",
        state: str = "",
        classes: set[str] | None = None,
    ) -> list[dict]:
        keywords = classes or _CLASSES_IMOVEIS_KEYWORDS
        if cnpj:
            results = self._search_by_document(cnpj, keywords)
            if results:
                return results
        return self._search_by_address(address, city, state, keywords)

    def _search_by_document(self, doc: str, keywords: set[str]) -> list[dict]:
        doc_clean = "".join(c for c in doc if c.isdigit())
        try:
            resp = httpx.get(
                f"{_BASE}/api_publica/processo",
                params={"numeroDocumento": doc_clean, "size": 20},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
            return [self._normalize(h["_source"]) for h in hits if self._matches_class(h, keywords)]
        except Exception:
            return []

    def _search_by_address(self, address: str, city: str, state: str, keywords: set[str]) -> list[dict]:
        query = f"{address} {city} {state}".strip()
        if not query:
            return []
        try:
            resp = httpx.get(
                f"{_BASE}/api_publica/processo",
                params={"query": query, "size": 10},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
            return [self._normalize(h["_source"]) for h in hits if self._matches_class(h, keywords)]
        except Exception:
            return []

    @staticmethod
    def _matches_class(hit: dict, keywords: set[str]) -> bool:
        classe_raw = hit.get("_source", {}).get("classe", {}).get("nome", "")
        classe = _norm(classe_raw)
        return any(kw in classe for kw in keywords)

    @staticmethod
    def _normalize(src: dict) -> dict:
        return {
            "numero": src.get("numeroProcesso", ""),
            "classe": src.get("classe", {}).get("nome", ""),
            "status": "ativo" if src.get("movimentos") else "arquivado",
            "tribunal": src.get("tribunal", ""),
        }
