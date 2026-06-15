"""Parser de hits DataJud para RawProperty."""
from __future__ import annotations

import json
from collections.abc import Iterator

from app.connectors.base import RawProperty
from app.core.logging import logger


class JudicialParser:
    def __init__(self, tribunal: str = "") -> None:
        self._tribunal = tribunal

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            return
        try:
            hits = json.loads(raw_bytes)
        except Exception as exc:
            logger.warning("judicial.parse_error", error=str(exc))
            return

        for hit in hits:
            process_number = hit.get("process_number", "")
            if not process_number:
                continue
            yield RawProperty(
                external_code=process_number,
                source_url=hit.get("process_url", source_url),
                bank_code=f"judicial_{self._tribunal[:3].lower()}",
                source_name=f"DataJud/{self._tribunal}",
                raw_data={
                    "title": hit.get("summary") or f"Hasta Pública — {self._tribunal}",
                    "city": hit.get("city", ""),
                    "state": hit.get("state", ""),
                    "minimum_value": hit.get("minimum_value"),
                    "auction_date": hit.get("hasta_date"),
                    "auctioneer_name": hit.get("auctioneer"),
                    "process_number": process_number,
                    "tribunal": self._tribunal,
                    "source_type": "judicial",
                    "official_url": hit.get("process_url", ""),
                },
                extra={
                    "source_type": "judicial",
                    "process_number": process_number,
                    "tribunal": self._tribunal,
                },
            )
