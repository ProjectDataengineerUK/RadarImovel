import hashlib
import json
from sqlalchemy.orm import Session
from app.models.property import Property


def compute_content_hash(normalized: dict) -> str:
    fields = {
        k: v for k, v in normalized.items()
        if k not in ("first_seen_at", "last_seen_at", "content_hash")
    }
    return hashlib.sha256(
        json.dumps(fields, sort_keys=True, default=str).encode()
    ).hexdigest()


def find_existing(session: Session, external_code: str, bank_id) -> Property | None:
    return (
        session.query(Property)
        .filter_by(external_code=external_code, bank_id=bank_id)
        .first()
    )


def is_duplicate(session: Session, content_hash: str) -> bool:
    return session.query(
        session.query(Property).filter_by(content_hash=content_hash).exists()
    ).scalar()
