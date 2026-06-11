"""Cloud Run Job: consome risk-events, calcula score de risco, persiste, publica risk-change-events."""
import json
import os
import uuid

from google.cloud import pubsub_v1

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.models.property import Property
from app.models.risk import PropertyRiskScore
from app.risk.calculator import calculate_risk

settings = get_settings()
log = configure_logging("calculate_risk")


def publish_event(topic: str, event: dict) -> None:
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(settings.pubsub_project_id, topic)
    publisher.publish(topic_path, json.dumps(event).encode())


def process_message(session, event: dict) -> str:
    property_id = uuid.UUID(event["property_id"])
    prop = session.query(Property).filter_by(id=property_id).first()
    if not prop:
        log.warning("calculate_risk.property_not_found", property_id=str(property_id))
        return "ignored"

    prev = session.query(PropertyRiskScore).filter_by(property_id=property_id).first()
    prev_score = float(prev.score_total) if prev else None
    prev_level = prev.risk_level if prev else None

    try:
        result = calculate_risk(prop, session, settings)
    except Exception as exc:
        log.error("calculate_risk.error", property_id=str(property_id), error=str(exc))
        return "error"

    indicators_dict = {k: v.model_dump() for k, v in result.indicators.items()}

    if prev:
        prev.score_total = result.score_total
        prev.score_juridico = result.score_juridico
        prev.score_fundiario = result.score_fundiario
        prev.score_fiscal = result.score_fiscal
        prev.score_ocupacao = result.score_ocupacao
        prev.score_socioeconomico = result.score_socioeconomico
        prev.score_mercado = result.score_mercado
        prev.risk_level = result.risk_level
        prev.indicators = indicators_dict
        prev.score_partial = result.score_partial
        prev.sources_consulted = result.sources_consulted
        prev.calculation_version = result.calculation_version
    else:
        session.add(
            PropertyRiskScore(
                property_id=property_id,
                score_total=result.score_total,
                score_juridico=result.score_juridico,
                score_fundiario=result.score_fundiario,
                score_fiscal=result.score_fiscal,
                score_ocupacao=result.score_ocupacao,
                score_socioeconomico=result.score_socioeconomico,
                score_mercado=result.score_mercado,
                risk_level=result.risk_level,
                indicators=indicators_dict,
                score_partial=result.score_partial,
                sources_consulted=result.sources_consulted,
                calculation_version=result.calculation_version,
            )
        )
    session.commit()

    if prev_score is not None and abs(result.score_total - prev_score) > settings.risk_score_change_threshold:
        publish_event(
            settings.pubsub_topic_risk_changes,
            {
                "property_id": str(property_id),
                "old_score": prev_score,
                "new_score": result.score_total,
                "old_level": prev_level,
                "new_level": result.risk_level,
            },
        )
        log.info(
            "calculate_risk.risk_change_published",
            property_id=str(property_id),
            old_score=prev_score,
            new_score=result.score_total,
        )

    log.info(
        "calculate_risk.done",
        property_id=str(property_id),
        score=result.score_total,
        level=result.risk_level,
        partial=result.score_partial,
    )
    return "done"


def run() -> None:
    dry_run = os.environ.get("DRY_RUN", "").lower() == "true"
    subscription = settings.pubsub_sub_risk
    log.info("job.start", subscription=subscription, dry_run=dry_run)

    subscriber = pubsub_v1.SubscriberClient()
    sub_path = subscriber.subscription_path(settings.pubsub_project_id, subscription)

    processed = errors = 0
    with subscriber:
        while True:
            resp = subscriber.pull(request={"subscription": sub_path, "max_messages": 10})
            if not resp.received_messages:
                break
            ack_ids = []
            for msg in resp.received_messages:
                try:
                    event = json.loads(msg.message.data.decode())
                    if not dry_run:
                        with SessionLocal() as session:
                            result = process_message(session, event)
                            if result != "error":
                                processed += 1
                            else:
                                errors += 1
                    ack_ids.append(msg.ack_id)
                except Exception as exc:
                    log.error("job.message_error", error=str(exc))
                    errors += 1

            if ack_ids:
                subscriber.acknowledge(request={"subscription": sub_path, "ack_ids": ack_ids})

    log.info("job.done", processed=processed, errors=errors)


if __name__ == "__main__":
    run()
