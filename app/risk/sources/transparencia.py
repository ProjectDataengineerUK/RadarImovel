"""IPTU scraping via portais de transparência municipal."""
import httpx
from bs4 import BeautifulSoup


class TransparenciaClient:
    def __init__(self, timeout: int = 10) -> None:
        self._timeout = timeout

    def get_iptu_debt(self, *, address: str, city: str, state: str, zipcode: str | None = None) -> dict | None:
        """Return {'has_debt': bool, 'debt_ratio': float | None} or None on failure."""
        handler = self._get_handler(state, city)
        try:
            return handler(address=address, city=city, zipcode=zipcode)
        except Exception:
            return None

    def _get_handler(self, state: str, city: str):
        if state.upper() == "SP" and "sao paulo" in city.lower():
            return self._sp_capital
        return self._generic

    def _sp_capital(self, *, address: str, city: str, zipcode: str | None = None) -> dict | None:
        resp = httpx.get(
            "https://consulta.prefeitura.sp.gov.br/cidadao/ficha_fiscal",
            params={"cep": zipcode or "", "logradouro": address},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        debt_tag = soup.find(string=lambda t: t and "débito" in t.lower())
        return {"has_debt": debt_tag is not None, "debt_ratio": None}

    def _generic(self, *, address: str, city: str, zipcode: str | None = None) -> dict | None:
        return None  # Coverage expanded in future iterations
