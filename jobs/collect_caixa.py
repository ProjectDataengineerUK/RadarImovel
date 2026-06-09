"""Cloud Run Job: coleta lista de imóveis da Caixa para uma UF."""
import json
import os
import sys
from datetime import UTC, datetime

from google.cloud import pubsub_v1, storage

from app.agents.change_detector import detect_and_record_changes
from app.agents.deduplicator import compute_content_hash, find_existing
from app.agents.score_agent import calculate_score
from app.connectors.caixa import CaixaConnector
from app.connectors.caixa.detail_scraper import CaixaDetailScraper
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.models.bank import Bank
from app.models.property import Property

settings = get_settings()
log = configure_logging("collect_caixa")


def upload_raw(bucket_name: str, uf: str, raw_bytes: bytes, url: str) -> str:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    filename = url.split("/")[-1] or f"lista_{uf}.xlsx"
    blob_path = f"raw/caixa/{uf}/{date_str}/{filename}"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(raw_bytes)
    return f"gs://{bucket_name}/{blob_path}"


def publish_event(project_id: str, topic: str, event: dict) -> None:
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic)
    publisher.publish(topic_path, json.dumps(event).encode())


def run(uf: str, fetch_detail: bool = True) -> None:
    log.info("job.start", uf=uf, fetch_detail=fetch_detail)
    connector = CaixaConnector(uf=uf)
    detail_scraper = CaixaDetailScraper() if fetch_detail else None

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
                            if detail_scraper and normalized.get("official_url"):
                                normalized = detail_scraper.enrich(normalized, normalized["official_url"])
                            prop = Property(bank_id=bank.id, **normalized)
                            session.add(prop)
                            session.flush()
                            publish_event(
                                settings.pubsub_project_id,
                                settings.pubsub_topic_events,
                                {"property_id": str(prop.id), "event_type": "new"},
                            )
                            if prop.edital_url:
                                publish_event(
                                    settings.pubsub_project_id,
                                    settings.pubsub_topic_editais,
                                    {
                                        "property_id": str(prop.id),
                                        "edital_url": prop.edital_url,
                                        "bank_id": str(bank.id),
                                    },
                                )
                            stats["new"] += 1

                        elif existing.content_hash != content_hash:
                            changes = detect_and_record_changes(session, existing, normalized)
                            for field, val in normalized.items():
                                if hasattr(existing, field):
                                    setattr(existing, field, val)
                            existing.last_seen_at = datetime.now(UTC)
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
                            existing.last_seen_at = datetime.now(UTC)

                    except Exception as exc:
                        stats["errors"] += 1
                        log.error("job.property_error", external_code=raw_prop.external_code, error=str(exc))

                session.commit()

            except Exception as exc:
                log.error("job.source_error", source_url=source_url, error=str(exc))

    log.info("job.done", uf=uf, **stats)


if __name__ == "__main__":
    # Thin-shim retrocompatível; delega à orquestração unificada collect_bank.
    # UF é opcional: sem UF o job processa todos os 27 estados em sequência.
    os.environ.setdefault("BANK", "caixa")
    from jobs.collect_bank import run as run_bank

    uf = os.environ.get("UF", "").strip() or None
    fetch_detail = os.environ.get("FETCH_DETAIL", "true").lower() != "false"
    run_bank("caixa", uf=uf.upper() if uf else None, fetch_detail=fetch_detail)
