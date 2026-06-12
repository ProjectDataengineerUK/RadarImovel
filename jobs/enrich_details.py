"""Cloud Run Job: enriquece imóveis sem situação de ocupação buscando página de detalhe."""
import os
import sys
import time

from app.connectors.caixa.detail_scraper import CaixaDetailScraper
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.models.bank import Bank
from app.models.property import Property

settings = get_settings()
log = configure_logging("enrich_details")

_BATCH = int(os.environ.get("BATCH_SIZE", "100"))
_DELAY_MS = int(os.environ.get("DELAY_MS", "500"))
_BANK = os.environ.get("BANK", "caixa")

_SCRAPERS = {"caixa": CaixaDetailScraper}


def run() -> None:
    log.info("job.start", bank=_BANK, batch_size=_BATCH, delay_ms=_DELAY_MS)
    if _BANK not in _SCRAPERS:
        log.warning("job.bank_not_supported", bank=_BANK, supported=list(_SCRAPERS))
        return
    scraper = _SCRAPERS[_BANK]()
    stats = {"processed": 0, "enriched": 0, "errors": 0, "skipped": 0}

    with SessionLocal() as session:
        query = (
            session.query(Property)
            .join(Bank, Property.bank_id == Bank.id)
            .filter(
                Bank.code == _BANK,
                Property.occupancy_status == "Não informado",
                Property.official_url.isnot(None),
                Property.official_url != "",
            )
            .order_by(Property.created_at.desc())
            .limit(_BATCH)
        )
        props = query.all()
        log.info("job.batch_loaded", count=len(props))

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

                # Sempre atualiza campos extras disponíveis (independente da ocupação)
                detail_fields = ("zipcode", "area_total", "area_private", "bedrooms",
                                 "parking_spaces", "edital_number", "auctioneer_name",
                                 "auction_date", "photo_url")
                for field in detail_fields:
                    if field in detail and detail[field] is not None and hasattr(prop, field):
                        setattr(prop, field, detail[field])

                if stats["processed"] % 20 == 0:
                    session.commit()
                    log.info("job.progress", **stats)

                time.sleep(_DELAY_MS / 1000)

            except Exception as exc:
                stats["errors"] += 1
                log.error("job.property_error", property_id=str(prop.id), url=url, error=str(exc))

        session.commit()

    log.info("job.done", bank=_BANK, **stats)


if __name__ == "__main__":
    run()
    sys.exit(0)
