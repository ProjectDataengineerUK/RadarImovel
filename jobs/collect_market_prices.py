"""Job mensal de ingestão de preços de mercado via FipeZap.

Uso:
    REFERENCE_MONTH=2026-06 python -m jobs.collect_market_prices
    python -m jobs.collect_market_prices   # usa mês atual
"""
from __future__ import annotations

import os
from datetime import datetime

from app.core.database import SessionLocal
from app.core.logging import logger
from app.services.fipezap import FipeZapClient

REFERENCE_MONTH = os.environ.get("REFERENCE_MONTH") or datetime.now().strftime("%Y-%m")


def main() -> None:
    logger.info("collect_market_prices.start", month=REFERENCE_MONTH)
    client = FipeZapClient()

    try:
        rows = client.fetch_index(REFERENCE_MONTH)
    except Exception as exc:
        logger.error("collect_market_prices.fetch_failed", error=str(exc))
        raise SystemExit(1)

    if not rows:
        logger.warning("collect_market_prices.empty_response", month=REFERENCE_MONTH)
        return

    from app.models.property import MarketPrice  # lazy import

    upserted = 0
    with SessionLocal() as session:
        for row in rows:
            city = row.get("city", "")
            uf = row.get("uf", "")
            ptype = row.get("property_type", "Apartamento")
            sqm_sale = row.get("price_per_sqm_sale")
            sqm_rent = row.get("price_per_sqm_rent")
            if not city or (sqm_sale is None and sqm_rent is None):
                continue

            existing = (
                session.query(MarketPrice)
                .filter_by(city=city, uf=uf, property_type=ptype, reference_month=REFERENCE_MONTH)
                .first()
            )
            if existing:
                if sqm_sale is not None:
                    existing.price_per_sqm_sale = sqm_sale
                    existing.price_per_sqm = sqm_sale
                if sqm_rent is not None:
                    existing.price_per_sqm_rent = sqm_rent
            else:
                session.add(
                    MarketPrice(
                        city=city,
                        uf=uf,
                        property_type=ptype,
                        price_per_sqm=sqm_sale,
                        price_per_sqm_sale=sqm_sale,
                        price_per_sqm_rent=sqm_rent,
                        reference_month=REFERENCE_MONTH,
                        source="fipezap",
                    )
                )
            upserted += 1

        session.commit()

    logger.info("collect_market_prices.done", month=REFERENCE_MONTH, upserted=upserted)


if __name__ == "__main__":
    main()
