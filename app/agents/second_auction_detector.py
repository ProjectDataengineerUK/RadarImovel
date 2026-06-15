"""Detecta quando um imóvel vai a 2ª praça e publica evento prioritário.

Invocado pelo change_detector imediatamente após persistir mudança de
minimum_value. Uma queda ≥ 40% no valor mínimo indica 2ª praça judicial
ou extrajudicial — os maiores descontos disponíveis no mercado.
"""
from __future__ import annotations

import json
import uuid
from decimal import Decimal

from app.core.logging import logger

_SEGUNDA_PRACA_THRESHOLD = 0.40


class SecondAuctionDetector:
    def detect(
        self,
        *,
        property_id: uuid.UUID,
        old_minimum: Decimal | None,
        new_minimum: Decimal | None,
        old_stage: str | None,
        session,
        publisher=None,
        topic: str | None = None,
    ) -> bool:
        """Retorna True se 2ª praça detectada; atualiza DB e publica evento."""
        if not old_minimum or not new_minimum or new_minimum <= 0:
            return False
        if old_stage == "segunda_praca":
            return False

        drop = float(old_minimum - new_minimum) / float(old_minimum)
        if drop < _SEGUNDA_PRACA_THRESHOLD:
            return False

        self._mark(property_id, session)
        self._publish(property_id, old_minimum, new_minimum, drop, publisher, topic)
        logger.info(
            "second_auction.detected",
            property_id=str(property_id),
            drop_pct=round(drop * 100, 1),
        )
        return True

    @staticmethod
    def _mark(property_id: uuid.UUID, session) -> None:
        from app.models.property import Property
        prop = session.get(Property, property_id)
        if prop:
            prop.auction_stage = "segunda_praca"
            session.flush()

    @staticmethod
    def _publish(
        property_id: uuid.UUID,
        old_minimum: Decimal,
        new_minimum: Decimal,
        drop: float,
        publisher=None,
        topic: str | None = None,
    ) -> None:
        payload = {
            "event_type": "segunda_praca",
            "property_id": str(property_id),
            "priority": "HIGH",
            "old_minimum": float(old_minimum),
            "new_minimum": float(new_minimum),
            "drop_pct": round(drop * 100, 1),
        }
        try:
            if publisher is None:
                from google.cloud import pubsub_v1
                from app.core.config import get_settings
                _settings = get_settings()
                publisher = pubsub_v1.PublisherClient()
                topic = publisher.topic_path(
                    _settings.pubsub_project_id, _settings.pubsub_topic_events
                )
            future = publisher.publish(topic, json.dumps(payload).encode())
            future.result(timeout=10)
        except Exception as exc:
            logger.warning("second_auction.publish_failed", error=str(exc))
