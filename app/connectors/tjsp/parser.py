"""Parser DataJud hits → RawProperty para TJSP."""
from __future__ import annotations

import json
from collections.abc import Iterator

from app.connectors.base import RawProperty
from app.core.logging import logger


class TJSPParser:
    def __init__(self, tribunal: str = "TJSP") -> None:
        self._tribunal = tribunal

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            return
        try:
            hits = json.loads(raw_bytes)
        except Exception as exc:
            logger.warning("tjsp.parse_json_error", error=str(exc))
            return

        if not isinstance(hits, list):
            hits = hits.get("hits", [])

        for hit in hits:
            process_number = hit.get("process_number") or hit.get("numero", "")
            if not process_number:
                continue
            yield RawProperty(
                external_code=f"TJSP-{process_number}",
                source_url=hit.get("process_url", source_url),
                bank_code="judicial_tjsp",
                source_name=f"DataJud/{self._tribunal}",
                raw_data={
                    "title": hit.get("summary") or f"Hasta Pública — {self._tribunal}",
                    "city": hit.get("city", ""),
                    "state": hit.get("state", "SP"),
                    "minimum_value": hit.get("minimum_value"),
                    "auction_date": hit.get("hasta_date"),
                    "auctioneer_name": hit.get("auctioneer"),
                    "process_number": process_number,
                    "tribunal": self._tribunal,
                    "official_url": hit.get("process_url", ""),
                },
                extra={"source_type": "judicial", "tribunal": self._tribunal},
            )
