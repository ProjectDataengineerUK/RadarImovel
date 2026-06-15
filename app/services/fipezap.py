"""Client FipeZap para preço/m² por cidade.

Estratégia primária: API JSON pública do FipeZap/ZAP.
Estratégia secundária: parse da tabela HTML da página de índices.
"""
from __future__ import annotations

import re
from decimal import Decimal

import httpx
from bs4 import BeautifulSoup

from app.core.logging import logger

_FIPEZAP_BASE = "https://fipezap.zapimoveis.com.br"
_TIMEOUT = 30
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
}


class FipeZapClient:
    def __init__(self, timeout: int = _TIMEOUT) -> None:
        self._timeout = timeout

    def fetch_index(self, reference_month: str) -> list[dict]:
        """Retorna preços/m² por cidade. reference_month: 'YYYY-MM'."""
        try:
            return self._fetch_api(reference_month)
        except Exception as exc:
            logger.warning("fipezap.api_unavailable", error=str(exc), fallback="scraping")
        try:
            return self._fetch_scraping()
        except Exception as exc:
            logger.error("fipezap.scraping_failed", error=str(exc))
            return []

    def _fetch_api(self, reference_month: str) -> list[dict]:
        resp = httpx.get(
            f"{_FIPEZAP_BASE}/api/v2/indicadores",
            params={"competencia": reference_month},
            headers=_HEADERS,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return self._parse_api_response(resp.json())

    def _fetch_scraping(self) -> list[dict]:
        resp = httpx.get(
            f"{_FIPEZAP_BASE}/indices",
            headers=_HEADERS,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return self._parse_html_table(BeautifulSoup(resp.content, "html.parser"))

    @staticmethod
    def _parse_api_response(data: dict) -> list[dict]:
        results = []
        for item in data.get("items", data.get("data", [])):
            city = item.get("cidade") or item.get("city")
            uf = item.get("uf") or item.get("state")
            if not city or not uf:
                continue
            results.append({
                "city": city.strip(),
                "uf": uf.strip().upper()[:2],
                "property_type": item.get("tipo", "geral"),
                "price_per_sqm_sale": _to_decimal(
                    item.get("precoVendaM2") or item.get("venda_m2")
                ),
                "price_per_sqm_rent": _to_decimal(
                    item.get("precoLocacaoM2") or item.get("locacao_m2")
                ),
            })
        return results

    @staticmethod
    def _parse_html_table(soup: BeautifulSoup) -> list[dict]:
        results = []
        table = soup.find("table")
        if not table:
            return results
        rows = table.find_all("tr")[1:]
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) < 3:
                continue
            results.append({
                "city": cells[0],
                "uf": cells[1].upper()[:2] if len(cells) > 1 else "",
                "property_type": "geral",
                "price_per_sqm_sale": _to_decimal(cells[2] if len(cells) > 2 else None),
                "price_per_sqm_rent": _to_decimal(cells[3] if len(cells) > 3 else None),
            })
        return results


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    s = re.sub(r"[^\d,.]", "", str(value))
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return Decimal(s)
    except Exception:
        return None


def get_market_prices_for_city(
    city: str,
    uf: str,
    property_type: str,
    session,
) -> object | None:
    """Busca o preço de mercado mais recente da tabela market_prices."""
    from sqlalchemy import text

    pt_norm = _normalize_property_type(property_type)
    row = session.execute(
        text("""
            SELECT price_per_sqm_sale, price_per_sqm_rent, reference_month
            FROM market_prices
            WHERE LOWER(city) = LOWER(:city) AND uf = :uf
              AND (property_type = :pt OR property_type = 'geral')
            ORDER BY reference_month DESC, property_type DESC
            LIMIT 1
        """),
        {"city": city, "uf": uf.upper(), "pt": pt_norm},
    ).fetchone()

    if not row and uf:
        row = session.execute(
            text("""
                SELECT price_per_sqm_sale, price_per_sqm_rent, reference_month
                FROM market_prices
                WHERE uf = :uf AND property_type = 'geral'
                ORDER BY reference_month DESC
                LIMIT 1
            """),
            {"uf": uf.upper()},
        ).fetchone()

    return row


def _normalize_property_type(pt: str | None) -> str:
    if not pt:
        return "geral"
    lower = pt.lower()
    if "apart" in lower:
        return "apartamento"
    if "casa" in lower:
        return "casa"
    return "geral"


async def get_selic_rate_async() -> Decimal:
    """Busca taxa Selic anual atual via API BCB."""
    try:
        resp = httpx.get(
            "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1",
            params={"formato": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data:
            rate_pct = Decimal(str(data[0]["valor"]))
            return rate_pct / 100
    except Exception as exc:
        logger.warning("selic.fetch_failed", error=str(exc))
    return Decimal("0.1050")
