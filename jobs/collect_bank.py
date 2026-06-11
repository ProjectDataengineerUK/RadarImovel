"""Cloud Run Job genérico: coleta imóveis de um banco selecionado por env BANK.

Substitui collect_caixa.py. Toda a orquestração (upload GCS, dedup, change
detection, publish) é bank-agnostic — o connector é resolvido via registry.
"""
import json
import os
import sys
from datetime import UTC, datetime

from google.cloud import pubsub_v1, storage

from app.agents.change_detector import detect_and_record_changes
from app.agents.deduplicator import compute_content_hash, find_existing
from app.agents.score_agent import calculate_score
from app.connectors import get_connector
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.models.bank import Bank
from app.models.property import Property

settings = get_settings()
log = configure_logging("collect_bank")


def upload_raw(bucket_name: str, bank: str, scope: str, raw_bytes: bytes, url: str) -> str:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    filename = url.split("/")[-1] or f"lista_{scope}"
    if "?" in filename:
        filename = filename.split("?")[0]
    blob_path = f"raw/{bank}/{scope}/{date_str}/{filename}"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(raw_bytes)
    return f"gs://{bucket_name}/{blob_path}"


def publish_event(project_id: str, topic: str, event: dict) -> None:
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic)
    publisher.publish(topic_path, json.dumps(event).encode())


def _build_detail_scraper(bank: str, fetch_detail: bool):
    if bank != "caixa" or not fetch_detail:
        return None
    try:
        from app.connectors.caixa.detail_scraper import CaixaDetailScraper

        return CaixaDetailScraper()
    except Exception as exc:
        log.warning("job.detail_scraper_unavailable", bank=bank, error=str(exc))
        return None


def run(bank: str, uf: str | None = None, fetch_detail: bool = True) -> None:
    bank = bank.lower().strip()
    dry_run = os.environ.get("DRY_RUN", "").lower() == "true"
    log.info("job.start", bank=bank, uf=uf, fetch_detail=fetch_detail, dry_run=dry_run)

    try:
        connector = get_connector(bank, uf=uf) if uf else get_connector(bank)
    except ValueError as exc:
        log.error("job.unknown_bank", bank=bank, error=str(exc))
        sys.exit(1)

    detail_scraper = _build_detail_scraper(bank, fetch_detail)

    with SessionLocal() as session:
        bank_row = session.query(Bank).filter_by(code=bank).first()
        if not bank_row:
            log.error("job.bank_not_found", bank=bank)
            sys.exit(1)
        if not bank_row.active:
            log.warning("job.bank_inactive", bank=bank)
            return

        stats = {"collected": 0, "new": 0, "changed": 0, "errors": 0}
        scope = uf or "nacional"
        sources = connector.discover_sources()

        for source_url in sources:
            try:
                raw_bytes = connector.fetch_raw(source_url)
                if not raw_bytes:
                    log.warning("job.empty_response", bank=bank, source_url=source_url)
                    continue

                if not dry_run:
                    gcs_path = upload_raw(
                        settings.gcs_bucket_raw, bank, scope, raw_bytes, source_url
                    )
                    log.info("job.raw_uploaded", gcs_path=gcs_path)

                for raw_prop in connector.parse(raw_bytes, source_url):
                    try:
                        normalized = connector.normalize(raw_prop)
                        normalized["opportunity_score"] = calculate_score(normalized)
                        content_hash = compute_content_hash(normalized)
                        normalized["content_hash"] = content_hash
                        stats["collected"] += 1

                        if dry_run:
                            continue

                        existing = find_existing(
                            session, raw_prop.external_code, bank_row.id
                        )

                        if existing is None:
                            if detail_scraper and normalized.get("official_url"):
                                normalized = detail_scraper.enrich(
                                    normalized, normalized["official_url"]
                                )
                            normalized.pop("bank_code", None)
                            prop = Property(bank_id=bank_row.id, **normalized)
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
                                        "bank_id": str(bank_row.id),
                                    },
                                )
                            publish_event(
                                settings.pubsub_project_id,
                                settings.pubsub_topic_risk,
                                {
                                    "property_id": str(prop.id),
                                    "lat": float(prop.latitude) if prop.latitude else None,
                                    "lng": float(prop.longitude) if prop.longitude else None,
                                    "city": prop.city,
                                    "state": prop.state,
                                },
                            )
                            stats["new"] += 1

                        elif existing.content_hash != content_hash:
                            changes = detect_and_record_changes(
                                session, existing, normalized
                            )
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
                                publish_event(
                                    settings.pubsub_project_id,
                                    settings.pubsub_topic_risk,
                                    {
                                        "property_id": str(existing.id),
                                        "lat": float(existing.latitude) if existing.latitude else None,
                                        "lng": float(existing.longitude) if existing.longitude else None,
                                        "city": existing.city,
                                        "state": existing.state,
                                    },
                                )
                                stats["changed"] += 1
                        else:
                            existing.last_seen_at = datetime.now(UTC)

                    except Exception as exc:
                        stats["errors"] += 1
                        log.error(
                            "job.property_error",
                            bank=bank,
                            external_code=raw_prop.external_code,
                            error=str(exc),
                        )

                if not dry_run:
                    session.commit()

            except Exception as exc:
                log.error("job.source_error", bank=bank, source_url=source_url, error=str(exc))

        if stats["collected"] == 0:
            log.warning("job.zero_properties", bank=bank, scope=scope)

    log.info("job.done", bank=bank, scope=scope, **stats)


if __name__ == "__main__":
    bank = os.environ.get("BANK", "").strip()
    if not bank:
        log.error("job.missing_bank")
        sys.exit(1)
    uf = os.environ.get("UF", "").strip() or None
    fetch_detail = os.environ.get("FETCH_DETAIL", "true").lower() != "false"
    run(bank, uf=uf.upper() if uf else None, fetch_detail=fetch_detail)
