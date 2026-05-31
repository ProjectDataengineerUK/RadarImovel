from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.property import Property, PropertyChange

MONITORED_FIELDS = [
    "current_value",
    "minimum_value",
    "discount_percent",
    "occupancy_status",
    "sale_modality",
    "status",
    "auction_date",
]


def detect_and_record_changes(
    session: Session, existing: Property, normalized: dict
) -> list[PropertyChange]:
    changes = []
    for field in MONITORED_FIELDS:
        old = getattr(existing, field)
        new = normalized.get(field)
        if str(old) != str(new):
            change = PropertyChange(
                property_id=existing.id,
                field_name=field,
                old_value=str(old) if old is not None else None,
                new_value=str(new) if new is not None else None,
                detected_at=datetime.now(timezone.utc),
            )
            session.add(change)
            changes.append(change)
    return changes
