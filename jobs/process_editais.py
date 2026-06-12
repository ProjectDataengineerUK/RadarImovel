"""Cloud Run Job: processa editais.

Consome `edital-events`, baixa o PDF, salva no GCS, extrai os campos com Gemini
2.0 Flash via Vertex AI, persiste em `Document.ai_summary`, recalcula o score
enriquecido da Property e publica `property-events {event_type: edital_processed}`.

Idempotência: se o Document já está `done`, faz ack e encerra sem reprocessar.
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

from app.agents.score_agent import calculate_enriched_score
from app.connectors.caixa.edital_extractor import extract_from_gcs
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.models.document import Document
from app.models.property import Property

settings = get_settings()
log = configure_logging("process_editais")


def download_pdf(url: str) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, settings.edital_max_retries + 1):
        try:
            resp = httpx.get(
                url, timeout=settings.edital_download_timeout_s, follow_redirects=True
            )
            resp.raise_for_status()
            return resp.content
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            log.warning("editais.download_retry", url=url, attempt=attempt, error=str(exc))
            if attempt < settings.edital_max_retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"download failed after {settings.edital_max_retries} attempts: {last_error}")


def upload_pdf(bank_code: str, state: str, property_id: str, pdf_bytes: bytes) -> str:
    client = storage.Client()
    bucket = client.bucket(settings.gcs_bucket_docs)
    blob_path = f"editais/{bank_code}/{state}/{property_id}.pdf"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(pdf_bytes, content_type="application/pdf")
    return f"gs://{settings.gcs_bucket_docs}/{blob_path}"


def publish_event(topic: str, event: dict) -> None:
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(settings.pubsub_project_id, topic)
    publisher.publish(topic_path, json.dumps(event).encode())


def _get_or_create_document(
    session: Session, property_id: uuid.UUID, bank_id: uuid.UUID, edital_url: str
) -> Document | None:
    doc = (
        session.query(Document)
        .filter_by(property_id=property_id, document_type="edital")
        .first()
    )
    if doc is None:
        doc = Document(
            property_id=property_id,
            bank_id=bank_id,
            document_type="edital",
            gcs_path="",
            original_url=edital_url,
            processing_status="processing",
        )
        session.add(doc)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            return (
                session.query(Document)
                .filter_by(property_id=property_id, document_type="edital")
                .first()
            )
    return doc


def process_message(session: Session, event: dict) -> str:
    """Processa uma mensagem. Retorna o status final do Document."""
    raw_pid = event.get("property_id")
    edital_url = event.get("edital_url")
    if not raw_pid:
        log.warning("editais.missing_property_id", event=event)
        return "ignored"

    property_id = uuid.UUID(raw_pid)
    prop = session.query(Property).filter_by(id=property_id).first()
    if not prop:
        log.warning("editais.property_not_found", property_id=raw_pid)
        return "ignored"

    edital_url = edital_url or prop.edital_url
    if not edital_url:
        log.warning("editais.no_edital_url", property_id=raw_pid)
        return "ignored"

    doc = _get_or_create_document(session, property_id, prop.bank_id, edital_url)
    if doc is None:
        return "ignored"
    if doc.processing_status == "done":
        log.info("editais.idempotent_skip", property_id=raw_pid)
        return "done_idempotent"

    doc.processing_status = "processing"
    doc.original_url = edital_url
    session.commit()

    started = time.monotonic()
    try:
        pdf_bytes = download_pdf(edital_url)
    except Exception as exc:  # noqa: BLE001
        doc.processing_status = "skipped"
        doc.processing_error = str(exc)[:2000]
        doc.processed_at = datetime.now(UTC)
        session.commit()
        log.warning("editais.skipped", property_id=raw_pid, error=str(exc))
        return "skipped"

    gcs_uri = upload_pdf(prop.bank.code, prop.state, raw_pid, pdf_bytes)
    doc.gcs_path = gcs_uri
    doc.file_size_bytes = len(pdf_bytes)
    doc.mime_type = "application/pdf"
    session.commit()

    try:
        extraction, model_used = extract_from_gcs(
            gcs_uri,
            property_external_code=prop.external_code,
            city=prop.city,
            state=prop.state,
            sale_modality=prop.sale_modality,
            appraisal_hint=prop.appraisal_value,
        )
    except Exception as exc:  # noqa: BLE001
        doc.processing_status = "failed"
        doc.processing_error = str(exc)[:2000]
        session.commit()
        log.error("editais.extraction_failed", property_id=raw_pid, error=str(exc))
        raise

    extraction_dict = extraction.model_dump(mode="json")
    doc.ai_summary = json.dumps(extraction_dict)
    doc.extraction_confidence = Decimal(str(round(extraction.extraction_confidence, 2)))
    doc.processing_status = "done"
    doc.processed_at = datetime.now(UTC)

    property_data = {
        "discount_percent": prop.discount_percent,
        "occupancy_status": prop.occupancy_status,
        "appraisal_value": prop.appraisal_value,
        "minimum_value": prop.minimum_value,
        "current_value": prop.current_value,
    }
    score, risk_level = calculate_enriched_score(property_data, extraction_dict)
    prop.opportunity_score = score
    prop.risk_level = risk_level

    if prop.auction_date is None and extraction.auction_date_1st:
        prop.auction_date = extraction.auction_date_1st
    if not prop.auctioneer_name and extraction.auctioneer_name:
        prop.auctioneer_name = extraction.auctioneer_name
    if prop.appraisal_value is None and extraction.appraisal_value:
        prop.appraisal_value = extraction.appraisal_value
    if not prop.edital_number and extraction.edital_number:
        prop.edital_number = extraction.edital_number

    session.commit()

    # Onda 4: indexa chunks no Vector Search para RAG
    try:
        from app.rag.indexer import index_document
        n_chunks = index_document(session, doc)
        session.commit()
        log.info("editais.rag_indexed", property_id=raw_pid, chunks=n_chunks)
    except Exception as exc:  # noqa: BLE001
        log.warning("editais.rag_index_error", property_id=raw_pid, error=str(exc))

    publish_event(
        settings.pubsub_topic_events,
        {"property_id": raw_pid, "event_type": "edital_processed"},
    )

    duration_ms = int((time.monotonic() - started) * 1000)
    log.info(
        "editais.done",
        property_id=raw_pid,
        processing_status="done",
        extraction_confidence=extraction.extraction_confidence,
        model_used=model_used,
        opportunity_score=score,
        risk_level=risk_level,
        duration_ms=duration_ms,
    )
    return "done"


def pull_and_process() -> None:
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        settings.pubsub_project_id, settings.pubsub_sub_editais
    )
    response = subscriber.pull(
        request={
            "subscription": subscription_path,
            "max_messages": settings.edital_batch_size,
        },
        timeout=30,
    )

    if not response.received_messages:
        log.info("editais.no_messages")
        return

    ack_ids = []
    for msg in response.received_messages:
        try:
            event = json.loads(msg.message.data.decode())
            with SessionLocal() as session:
                process_message(session, event)
            ack_ids.append(msg.ack_id)
        except Exception as exc:  # noqa: BLE001
            log.error("editais.message_error", error=str(exc))
            # nack implícito — Pub/Sub retentará (até DLQ)

    if ack_ids:
        subscriber.acknowledge(
            request={"subscription": subscription_path, "ack_ids": ack_ids}
        )
        log.info("editais.acked", count=len(ack_ids))


if __name__ == "__main__":
    try:
        pull_and_process()
    except Exception as exc:  # noqa: BLE001
        log.error("editais.fatal", error=str(exc))
        sys.exit(1)
