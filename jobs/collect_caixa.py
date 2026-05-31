"""Cloud Run Job: coleta lista de imóveis da Caixa para uma UF."""
import os
import sys
import json
from datetime import datetime, timezone
from google.cloud import storage, pubsub_v1
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.connectors.caixa import CaixaConnector
from app.agents.deduplicator import compute_content_hash, find_existing, is_duplicate
from app.agents.change_detector import detect_and_record_changes
from app.agents.score_agent import calculate_score
from app.models.bank import Bank
from app.models.property import Property

settings = get_settings()
log = configure_logging("collect_caixa")


def upload_raw(bucket_name: str, uf: str, raw_bytes: bytes, url: str) -> str:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = url.split("/")[-1] or f"lista_{uf}.xlsx"
    blob_path = f"raw/caixa/{uf}/{date_str}/{filename}"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(raw_bytes)
    return f"gs://{bucket_name}/{blob_path}"


def publish_event(project_id: str, topic: str, event: dict) -> None:
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic)
    publisher.publish(topic_path, json.dumps(event).encode())


def run(uf: str) -> None:
    log.info("job.start", uf=uf)
    connector = CaixaConnector(uf=uf)

    with SessionLocal() as session:
        bank = session.query(Bank).filter_by(code="caixa").first()
        if not bank:
            log.error("job.bank_not_found", bank="caixa")
            sys.exit(1)

        stats = {"collected": 0, "new": 0, "changed": 0, "errors": 0}
        sources = connector.discover_sources()

        for source_url in sources:
            try:
                raw_bytes = connector.fetch_raw(source_url)
                if not raw_bytes:
                    log.warning("job.empty_response", source_url=source_url)
                    continue

                gcs_path = upload_raw(settings.gcs_bucket_raw, uf, raw_bytes, source_url)
                log.info("job.raw_uploaded", gcs_path=gcs_path)

                for raw_prop in connector.parse(raw_bytes, source_url):
                    try:
                        normalized = connector.normalize(raw_prop)
                        normalized["opportunity_score"] = calculate_score(normalized)
                        content_hash = compute_content_hash(normalized)
                        normalized["content_hash"] = content_hash
                        stats["collected"] += 1

                        existing = find_existing(session, raw_prop.external_code, bank.id)

                        if existing is None:
                            prop = Property(bank_id=bank.id, **normalized)
                            session.add(prop)
                            session.flush()
                            publish_event(
                                settings.pubsub_project_id,
                                settings.pubsub_topic_events,
                                {"property_id": str(prop.id), "event_type": "new"},
                            )
                            stats["new"] += 1

                        elif existing.content_hash != content_hash:
                            changes = detect_and_record_changes(session, existing, normalized)
                            for field, val in normalized.items():
                                if hasattr(existing, field):
                                    setattr(existing, field, val)
                            existing.last_seen_at = datetime.now(timezone.utc)
                            if changes:
                                publish_event(
                                    settings.pubsub_project_id,
                                    settings.pubsub_topic_events,
                                    {
                                        "property_id": str(existing.id),
                                        "event_type": "changed",
                                        "changes": [c.field_name for c in changes],
                                    },
                                )
                                stats["changed"] += 1
                        else:
                            existing.last_seen_at = datetime.now(timezone.utc)

                    except Exception as exc:
                        stats["errors"] += 1
                        log.error("job.property_error", external_code=raw_prop.external_code, error=str(exc))

                session.commit()

            except Exception as exc:
                log.error("job.source_error", source_url=source_url, error=str(exc))

    log.info("job.done", uf=uf, **stats)


if __name__ == "__main__":
    uf = os.environ.get("UF", "")
    if not uf:
        log.error("job.missing_uf")
        sys.exit(1)
    run(uf.upper())
