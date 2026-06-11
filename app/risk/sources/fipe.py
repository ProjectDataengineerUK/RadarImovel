"""Fipe ZAP preço/m² por cidade — fonte opcional; falha silenciosa."""
import httpx

_BASE = "https://glue-api.zapimoveis.com.br/v2/listings"


class FipeClient:
    def __init__(self, timeout: int = 8) -> None:
        self._timeout = timeout

    def get_price_per_sqm(self, city: str, state: str) -> float | None:
        """Return average price/m² or None if unavailable."""
        try:
            resp = httpx.get(
                _BASE,
                params={"city": city, "state": state, "listingType": "USED", "size": 1},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            avg = data.get("search", {}).get("result", {}).get("listings", [{}])
            if avg:
                unit = avg[0].get("listing", {}).get("usableArea", [None])[0]
                price = avg[0].get("listing", {}).get("prices", {}).get("period")
                if unit and price:
                    return float(price) / float(unit)
        except Exception:
            pass
        return None
