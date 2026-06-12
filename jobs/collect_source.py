"""Cloud Run Job genérico: coleta imóveis de qualquer fonte (banco ou leiloeiro).

Variáveis de ambiente:
  SOURCE   — código da fonte (ex: "zuk", "caixa", "mega")
  UF       — filtro por UF (opcional; não aplicável a todos os conectores)
  DRY_RUN  — "true" para não persistir nem publicar

Diferença vs collect_bank.py:
  - Usa SOURCE_REGISTRY (inclui leiloeiros)
  - Bloqueia fontes com tos_compliant=False a menos que FORCE_TOS=true
  - Usa deduplicator.process_property (v2: multi-offer + best_price)
"""
import json
import os
import sys
from datetime import UTC, datetime

from google.cloud import pubsub_v1, storage

from app.agents.deduplicator import compute_content_hash, process_property
from app.agents.score_agent import calculate_score
from app.connectors import get_source
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.models.bank import Bank

settings = get_settings()
log = configure_logging("collect_source")


def upload_raw(bucket_name: str, source: str, scope: str, raw_bytes: bytes, url: str) -> str:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    filename = url.split("/")[-1] or f"lista_{scope}"
    if "?" in filename:
        filename = filename.split("?")[0]
    blob_path = f"raw/{source}/{scope}/{date_str}/{filename}"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(raw_bytes)
    return f"gs://{bucket_name}/{blob_path}"


def publish_event(project_id: str, topic: str, event: dict) -> None:
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic)
    publisher.publish(topic_path, json.dumps(event).encode())


def run(source_code: str, uf: str | None = None) -> None:
    source_code = source_code.lower().strip()
    dry_run = os.environ.get("DRY_RUN", "").lower() == "true"
    force_tos = os.environ.get("FORCE_TOS", "").lower() == "true"
    log.info("job.start", source=source_code, uf=uf, dry_run=dry_run)

    try:
        connector = get_source(source_code, uf=uf) if uf else get_source(source_code)
    except ValueError as exc:
        log.error("job.unknown_source", source=source_code, error=str(exc))
        sys.exit(1)

    with SessionLocal() as session:
        source_row = session.query(Bank).filter_by(code=source_code).first()
        if not source_row:
            log.error("job.source_not_found", source=source_code)
            sys.exit(1)
        if not source_row.active:
            log.warning("job.source_inactive", source=source_code)
            return
        if not source_row.tos_compliant and not force_tos:
            log.warning(
                "job.tos_blocked",
                source=source_code,
                hint="Defina FORCE_TOS=true após validação jurídica do ToS",
            )
            return

        scope = uf or "all"
        stats = {"collected": 0, "new": 0, "updated": 0, "errors": 0}

        for source_url in connector.discover_sources():
            try:
                raw_bytes = connector.fetch_raw(source_url)
                if not raw_bytes:
                    continue

                if not dry_run and settings.gcs_bucket_name:
                    upload_raw(settings.gcs_bucket_name, source_code, scope, raw_bytes, source_url)

                for raw_prop in connector.parse(raw_bytes, source_url):
                    try:
                        stats["collected"] += 1
                        normalized = connector.normalize(raw_prop)
                        normalized.setdefault("bank_code", source_code)

                        content_hash = compute_content_hash(
                            {**normalized, "source_id": str(source_row.id)}
                        )
                        normalized["content_hash"] = content_hash

                        if not dry_run:
                            prop, is_new = process_property(
                                session,
                                normalized,
                                source_row,
                                raw_prop.external_code,
                            )
                            if is_new:
                                prop.opportunity_score = calculate_score(normalized)
                                publish_event(
                                    settings.pubsub_project_id,
                                    settings.pubsub_topic_events,
                                    {
                                        "property_id": str(prop.id),
                                        "event_type": "new",
                                        "source": source_code,
                                    },
                                )
                                stats["new"] += 1
                            else:
                                stats["updated"] += 1

                    except Exception as exc:
                        stats["errors"] += 1
                        log.error(
                            "job.property_error",
                            source=source_code,
                            external_code=raw_prop.external_code,
                            error=str(exc),
                        )

                if not dry_run:
                    session.commit()

            except Exception as exc:
                log.error("job.source_error", source=source_code, url=source_url, error=str(exc))

        if stats["collected"] == 0:
            log.warning("job.zero_properties", source=source_code, scope=scope)

    log.info("job.done", source=source_code, scope=scope, **stats)


if __name__ == "__main__":
    source = os.environ.get("SOURCE", "").strip()
    if not source:
        log.error("job.missing_source")
        sys.exit(1)
    uf = os.environ.get("UF", "").strip() or None
    run(source, uf=uf.upper() if uf else None)
