"""Cloud Run Job: enriquece imóveis sem situação de ocupação e sem coordenadas geográficas."""
import asyncio
import os
import sys
import time

from app.connectors.caixa.detail_scraper import CaixaDetailScraper
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.models.bank import Bank
from app.models.property import Property
from app.services.geocoding import _geocode_nominatim, cep_to_latlong

settings = get_settings()
log = configure_logging("enrich_details")

_BATCH = int(os.environ.get("BATCH_SIZE", "100"))
_DELAY_MS = int(os.environ.get("DELAY_MS", "500"))
_BANK = os.environ.get("BANK", "caixa")
_GEO_BATCH = int(os.environ.get("GEO_BATCH_SIZE", "300"))
_GEO_DELAY_MS = int(os.environ.get("GEO_DELAY_MS", "1100"))  # Nominatim: 1 req/s
_SKIP_GEOCODE = os.environ.get("SKIP_GEOCODE", "").lower() == "true"

_SCRAPERS = {"caixa": CaixaDetailScraper}


def _try_geocode(prop: Property) -> tuple[float, float] | None:
    """CEP via ViaCEP first, then city+state via Nominatim as fallback."""
    if prop.zipcode:
        try:
            result = asyncio.run(cep_to_latlong(prop.zipcode))
            if result:
                return result
        except Exception:
            pass
    if prop.city and prop.state:
        try:
            result = asyncio.run(_geocode_nominatim(f"{prop.city}, {prop.state}, Brasil"))
            if result:
                return result
        except Exception:
            pass
    return None


def run() -> None:
    log.info("job.start", bank=_BANK, batch_size=_BATCH, delay_ms=_DELAY_MS)

    # --- Phase 1: occupancy enrichment (Caixa only) ---
    if _BANK in _SCRAPERS:
        scraper = _SCRAPERS[_BANK]()
        stats = {"processed": 0, "enriched": 0, "errors": 0, "skipped": 0}

        with SessionLocal() as session:
            props = (
                session.query(Property)
                .join(Bank, Property.bank_id == Bank.id)
                .filter(
                    Bank.code == _BANK,
                    Property.occupancy_status == "Não informado",
                    Property.official_url.isnot(None),
                    Property.official_url != "",
                )
                .order_by(Property.first_seen_at.desc())
                .limit(_BATCH)
                .all()
            )
            log.info("occupancy.batch_loaded", count=len(props))

            for prop in props:
                stats["processed"] += 1
                url = prop.official_url
                if not url or not url.startswith("http"):
                    stats["skipped"] += 1
                    continue

                try:
                    html = scraper.fetch(url)
                    detail = scraper.parse(html) if html else {}
                    occupancy = detail.get("occupancy_status")
                    if occupancy:
                        prop.occupancy_status = occupancy
                        stats["enriched"] += 1
                    else:
                        stats["skipped"] += 1

                    detail_fields = (
                        "zipcode", "area_total", "area_private", "bedrooms",
                        "parking_spaces", "edital_number", "auctioneer_name",
                        "auction_date", "photo_url",
                    )
                    for field in detail_fields:
                        if field in detail and detail[field] is not None and hasattr(prop, field):
                            setattr(prop, field, detail[field])

                    if stats["processed"] % 20 == 0:
                        session.commit()
                        log.info("occupancy.progress", **stats)

                    time.sleep(_DELAY_MS / 1000)

                except Exception as exc:
                    stats["errors"] += 1
                    log.error("occupancy.property_error", property_id=str(prop.id), url=url, error=str(exc))

            session.commit()

        log.info("occupancy.done", bank=_BANK, **stats)
    else:
        log.info("occupancy.skipped", bank=_BANK, reason="no scraper for this bank")

    # --- Phase 2: geocoding (all banks, properties without lat/lng) ---
    if _SKIP_GEOCODE:
        log.info("geocoding.skipped", reason="SKIP_GEOCODE=true")
        return

    geo = {"checked": 0, "geocoded": 0, "failed": 0}
    with SessionLocal() as session:
        props_no_geo = (
            session.query(Property)
            .filter(Property.latitude.is_(None))
            .order_by(Property.first_seen_at.desc())
            .limit(_GEO_BATCH)
            .all()
        )
        log.info("geocoding.batch_start", count=len(props_no_geo))

        for prop in props_no_geo:
            geo["checked"] += 1
            coords = _try_geocode(prop)
            if coords:
                prop.latitude, prop.longitude = coords
                geo["geocoded"] += 1
            else:
                geo["failed"] += 1

            if geo["checked"] % 20 == 0:
                session.commit()
                log.info("geocoding.progress", **geo)

            time.sleep(_GEO_DELAY_MS / 1000)

        session.commit()

    log.info("geocoding.done", **geo)


if __name__ == "__main__":
    run()
    sys.exit(0)
