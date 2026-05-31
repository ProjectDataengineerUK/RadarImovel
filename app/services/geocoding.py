import httpx
from app.core.logging import logger


async def cep_to_latlong(cep: str) -> tuple[float, float] | None:
    """Resolve CEP via ViaCEP, depois geocodifica endereço via Nominatim."""
    address = await _resolve_address_from_cep(cep)
    if not address:
        return None
    return await _geocode_nominatim(address)


async def _resolve_address_from_cep(cep: str) -> str | None:
    cleaned = "".join(filter(str.isdigit, cep))
    if len(cleaned) != 8:
        return None
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"https://viacep.com.br/ws/{cleaned}/json/")
            if r.status_code != 200:
                return None
            data = r.json()
            parts = [data.get("logradouro"), data.get("localidade"), data.get("uf"), "Brasil"]
            return ", ".join(p for p in parts if p)
    except Exception as exc:
        logger.warning("geocoding.viacep_failed", cep=cep, error=str(exc))
        return None


async def _geocode_nominatim(address: str) -> tuple[float, float] | None:
    headers = {"User-Agent": "RadarImovel/1.0 (contato@radarimovel.com.br)"}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1},
                headers=headers,
            )
            results = r.json()
            if results:
                return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as exc:
        logger.warning("geocoding.nominatim_failed", address=address, error=str(exc))
    return None
