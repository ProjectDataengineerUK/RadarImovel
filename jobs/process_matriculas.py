"""Cloud Run Job: processa matrículas de imóveis via Gemini.

Consome `matricula-events`, baixa o PDF, salva no GCS, extrai os dados
com Gemini via Vertex AI, persiste em `Document.ai_summary` com type
`matricula` e publica `property-events {event_type: matricula_processed}`.

Idempotência: se o Document `matricula` já está `done`, faz ack e encerra.
"""
import json
import sys
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import httpx
from google.cloud import pubsub_v1, storage
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.connectors.caixa.matricula_extractor import extract_matricula_from_gcs
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.models.document import Document
from app.models.property import Property

settings = get_settings()
log = configure_logging("process_matriculas")


def download_pdf(url: str) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, settings.edital_max_retries + 1):
        try:
            resp = httpx.get(url, timeout=settings.edital_download_timeout_s, follow_redirects=True)
            resp.raise_for_status()
            return resp.content
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            log.warning("matriculas.download_retry", url=url, attempt=attempt, error=str(exc))
            if attempt < settings.edital_max_retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"download failed after {settings.edital_max_retries} attempts: {last_error}")


def upload_pdf(property_id: str, pdf_bytes: bytes) -> str:
    client = storage.Client()
    bucket = client.bucket(settings.gcs_bucket_docs)
    blob_path = f"matriculas/{property_id}.pdf"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(pdf_bytes, content_type="application/pdf")
    return f"gs://{settings.gcs_bucket_docs}/{blob_path}"


def publish_event(topic: str, event: dict) -> None:
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(settings.pubsub_project_id, topic)
    publisher.publish(topic_path, json.dumps(event).encode())


def _get_or_create_document(session: Session, property_id: uuid.UUID, bank_id: uuid.UUID, url: str) -> Document | None:
    doc = session.query(Document).filter_by(property_id=property_id, document_type="matricula").first()
    if doc is None:
        doc = Document(
            property_id=property_id,
            bank_id=bank_id,
            document_type="matricula",
            gcs_path="",
            original_url=url,
            processing_status="processing",
        )
        session.add(doc)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            return session.query(Document).filter_by(property_id=property_id, document_type="matricula").first()
    return doc


def process_message(session: Session, event: dict) -> str:
    raw_pid = event.get("property_id")
    matricula_url = event.get("matricula_url")
    if not raw_pid:
        log.warning("matriculas.missing_property_id", event=event)
        return "ignored"

    property_id = uuid.UUID(raw_pid)
    prop = session.query(Property).filter_by(id=property_id).first()
    if not prop:
        log.warning("matriculas.property_not_found", property_id=raw_pid)
        return "ignored"

    if not matricula_url:
        log.warning("matriculas.no_url", property_id=raw_pid)
        return "ignored"

    doc = _get_or_create_document(session, property_id, prop.bank_id, matricula_url)
    if doc is None:
        return "ignored"
    if doc.processing_status == "done":
        log.info("matriculas.idempotent_skip", property_id=raw_pid)
        return "done_idempotent"

    doc.processing_status = "processing"
    session.commit()

    started = time.monotonic()
    try:
        pdf_bytes = download_pdf(matricula_url)
    except Exception as exc:  # noqa: BLE001
        doc.processing_status = "skipped"
        doc.processing_error = str(exc)[:2000]
        doc.processed_at = datetime.now(UTC)
        session.commit()
        log.warning("matriculas.skipped", property_id=raw_pid, error=str(exc))
        return "skipped"

    gcs_uri = upload_pdf(raw_pid, pdf_bytes)
    doc.gcs_path = gcs_uri
    doc.file_size_bytes = len(pdf_bytes)
    doc.mime_type = "application/pdf"
    session.commit()

    try:
        extraction, model_used = extract_matricula_from_gcs(
            gcs_uri, property_external_code=prop.external_code
        )
    except Exception as exc:  # noqa: BLE001
        doc.processing_status = "failed"
        doc.processing_error = str(exc)[:2000]
        session.commit()
        log.error("matriculas.extraction_failed", property_id=raw_pid, error=str(exc))
        raise

    extraction_dict = extraction.model_dump(mode="json")
    doc.ai_summary = json.dumps({**extraction_dict, "_model_used": model_used})
    doc.extraction_confidence = Decimal(str(round(extraction.extraction_confidence, 2)))
    doc.processing_status = "done"
    doc.processed_at = datetime.now(UTC)
    session.commit()

    publish_event(
        settings.pubsub_topic_events,
        {"property_id": raw_pid, "event_type": "matricula_processed"},
    )

    duration_ms = int((time.monotonic() - started) * 1000)
    log.info(
        "matriculas.done",
        property_id=raw_pid,
        model_used=model_used,
        confidence=extraction.extraction_confidence,
        onus_count=len(extraction.onus_reais),
        duration_ms=duration_ms,
    )
    return "done"


def pull_and_process() -> None:
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        settings.pubsub_project_id, settings.pubsub_sub_matriculas
    )
    response = subscriber.pull(
        request={"subscription": subscription_path, "max_messages": settings.edital_batch_size},
        timeout=30,
    )

    if not response.received_messages:
        log.info("matriculas.no_messages")
        return

    ack_ids = []
    for msg in response.received_messages:
        try:
            event = json.loads(msg.message.data.decode())
            with SessionLocal() as session:
                process_message(session, event)
            ack_ids.append(msg.ack_id)
        except Exception as exc:  # noqa: BLE001
            log.error("matriculas.message_error", error=str(exc))

    if ack_ids:
        subscriber.acknowledge(request={"subscription": subscription_path, "ack_ids": ack_ids})
        log.info("matriculas.acked", count=len(ack_ids))


if __name__ == "__main__":
    try:
        pull_and_process()
    except Exception as exc:  # noqa: BLE001
        log.error("matriculas.fatal", error=str(exc))
        sys.exit(1)
