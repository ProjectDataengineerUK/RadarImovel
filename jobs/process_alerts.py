"""Cloud Run Job: consome eventos de property-events e envia alertas Telegram."""
import asyncio
import json
import sys
from google.cloud import pubsub_v1
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.agents.alert_agent import process_property_event, process_risk_change_event

settings = get_settings()
log = configure_logging("process_alerts")


def _pull_and_process(subscription_name: str, handler) -> None:
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        settings.pubsub_project_id,
        subscription_name,
    )

    response = subscriber.pull(
        request={"subscription": subscription_path, "max_messages": 50},
        timeout=30,
    )

    if not response.received_messages:
        log.info("alerts.no_messages", subscription=subscription_name)
        return

    ack_ids = []
    for msg in response.received_messages:
        try:
            event = json.loads(msg.message.data.decode())
            log.info("alerts.processing", subscription=subscription_name, event=event)
            asyncio.run(handler(event))
            ack_ids.append(msg.ack_id)
        except Exception as exc:
            log.error("alerts.event_error", subscription=subscription_name, error=str(exc))
            # nack implícito — Pub/Sub vai retentativa automaticamente

    if ack_ids:
        subscriber.acknowledge(
            request={"subscription": subscription_path, "ack_ids": ack_ids}
        )
        log.info("alerts.acked", subscription=subscription_name, count=len(ack_ids))


def pull_and_process() -> None:
    _pull_and_process(f"{settings.pubsub_topic_events}-sub", process_property_event)
    _pull_and_process(settings.pubsub_sub_risk_changes, process_risk_change_event)


if __name__ == "__main__":
    try:
        pull_and_process()
    except Exception as exc:
        log.error("alerts.fatal", error=str(exc))
        sys.exit(1)
