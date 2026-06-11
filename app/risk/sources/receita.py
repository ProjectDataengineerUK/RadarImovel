"""Receita Federal CNPJ API — verifica CNPJs ativos no endereço do imóvel."""
import httpx

_BASE = "https://publica.cnpj.ws/cnpj"


class ReceitaClient:
    def __init__(self, timeout: int = 10) -> None:
        self._timeout = timeout

    def get_cnpj(self, cnpj: str) -> dict | None:
        cnpj_clean = "".join(c for c in cnpj if c.isdigit())
        try:
            resp = httpx.get(f"{_BASE}/{cnpj_clean}", timeout=self._timeout)
            resp.raise_for_status()
            data = resp.json()
            return {
                "cnpj": cnpj_clean,
                "razao_social": data.get("razao_social", ""),
                "situacao": data.get("descricao_situacao_cadastral", ""),
                "ativa": data.get("descricao_situacao_cadastral", "").upper() == "ATIVA",
                "logradouro": data.get("logradouro", ""),
                "municipio": data.get("municipio", ""),
                "uf": data.get("uf", ""),
            }
        except Exception:
            return None
