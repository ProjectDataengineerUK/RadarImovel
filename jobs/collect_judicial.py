"""Job de coleta de hastas públicas de tribunais via DataJud.

Uso:
    TRIBUNAL=TRT2 python -m jobs.collect_judicial
    TRIBUNAL=TJSP DAYS_BACK=60 python -m jobs.collect_judicial
"""
from __future__ import annotations

import os

from jobs.collect_bank import run_connector

from app.connectors import SOURCE_REGISTRY
from app.core.database import SessionLocal
from app.core.logging import logger

TRIBUNAL = os.environ.get("TRIBUNAL", "TRT2").upper()
DAYS_BACK = int(os.environ.get("DAYS_BACK", "30"))


def main() -> None:
    source_key = TRIBUNAL.lower()
    if source_key not in SOURCE_REGISTRY:
        source_key = "judicial"

    connector_cls = SOURCE_REGISTRY.get(source_key)
    if connector_cls is None:
        logger.error("collect_judicial.unknown_tribunal", tribunal=TRIBUNAL)
        raise SystemExit(1)

    logger.info("collect_judicial.start", tribunal=TRIBUNAL, days_back=DAYS_BACK)
    try:
        connector = connector_cls(tribunal=TRIBUNAL, days_back=DAYS_BACK)  # type: ignore[call-arg]
    except TypeError:
        try:
            connector = connector_cls(days_back=DAYS_BACK)  # type: ignore[call-arg]
        except TypeError:
            connector = connector_cls()

    bank_code = "judicial" if source_key == "judicial" else source_key
    with SessionLocal() as session:
        total = run_connector(connector, session, bank_code=bank_code)
        logger.info("collect_judicial.done", tribunal=TRIBUNAL, total=total)


if __name__ == "__main__":
    main()
