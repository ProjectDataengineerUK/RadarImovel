"""Deduplicator v2: 2-stage matching + PropertyOffer upsert + best_price refresh."""
import hashlib
import json
from decimal import Decimal
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.models.bank import Bank
from app.models.property import Property, PropertyOffer
from app.core.logging import logger

TRGM_THRESHOLD = 0.85
TRGM_AMBIGUOUS_FLOOR = 0.70


# ── Backward-compat helpers (used by collect_bank.py) ─────────────────────────

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


# ── v2 helpers ────────────────────────────────────────────────────────────────

def _geo_key(lat, lng) -> str | None:
    """~100m proximity bucket (3 decimal places ≈ 111m)."""
    if lat is None or lng is None:
        return None
    return f"{round(float(lat), 3)},{round(float(lng), 3)}"


def _title_sim(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _upsert_offer(
    session: Session,
    property_id,
    source_id,
    normalized: dict,
    ext_code: str,
) -> PropertyOffer:
    offer = (
        session.query(PropertyOffer)
        .filter_by(property_id=property_id, source_id=source_id)
        .first()
    )
    if offer:
        offer.price = normalized.get("current_value", offer.price)
        offer.modality = normalized.get("sale_modality", offer.modality)
        offer.auction_date = normalized.get("auction_date", offer.auction_date)
        offer.official_url = normalized.get("official_url", offer.official_url) or offer.official_url
        offer.active = True
        offer.external_code = ext_code
    else:
        offer = PropertyOffer(
            property_id=property_id,
            source_id=source_id,
            price=normalized.get("current_value") or Decimal("0"),
            modality=normalized.get("sale_modality") or "Leilão",
            auction_date=normalized.get("auction_date"),
            official_url=normalized.get("official_url") or "",
            external_code=ext_code,
            active=True,
        )
        session.add(offer)
    return offer


def _refresh_best_price(session: Session, property_id) -> None:
    offers = (
        session.query(PropertyOffer)
        .filter_by(property_id=property_id, active=True)
        .all()
    )
    if not offers:
        return
    best = min(o.price for o in offers)
    prop = session.get(Property, property_id)
    if prop:
        prop.best_price = best


def _create_property(session: Session, normalized: dict, source_row: Bank, ext_code: str) -> Property:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    content_hash = compute_content_hash({**normalized, "source_id": str(source_row.id)})
    prop = Property(
        bank_id=source_row.id,
        source_id=None,
        external_code=ext_code,
        title=normalized.get("title"),
        property_type=normalized.get("property_type") or "Imóvel",
        address=normalized.get("address"),
        city=normalized.get("city") or "",
        state=normalized.get("state") or "",
        zipcode=normalized.get("zipcode"),
        latitude=normalized.get("latitude"),
        longitude=normalized.get("longitude"),
        area_total=normalized.get("area_total"),
        area_private=normalized.get("area_private"),
        bedrooms=normalized.get("bedrooms"),
        parking_spaces=normalized.get("parking_spaces"),
        appraisal_value=normalized.get("appraisal_value"),
        minimum_value=normalized.get("minimum_value") or Decimal("0"),
        current_value=normalized.get("current_value") or Decimal("0"),
        discount_percent=normalized.get("discount_percent"),
        occupancy_status=normalized.get("occupancy_status") or "Desconhecido",
        sale_modality=normalized.get("sale_modality") or "Leilão",
        edital_number=normalized.get("edital_number"),
        auction_date=normalized.get("auction_date"),
        auctioneer_name=normalized.get("auctioneer_name"),
        auctioneer_url=normalized.get("auctioneer_url"),
        official_url=normalized.get("official_url") or "",
        photo_url=normalized.get("photo_url"),
        edital_url=normalized.get("edital_url"),
        status="active",
        content_hash=content_hash,
        first_seen_at=now,
        last_seen_at=now,
    )
    session.add(prop)
    session.flush()
    return prop


# ── v2 main entry point ───────────────────────────────────────────────────────

def process_property(
    session: Session,
    normalized: dict,
    source_row: Bank,
    ext_code: str,
    trgm_threshold: float = TRGM_THRESHOLD,
) -> tuple[Property, bool]:
    """
    Dedup v2: returns (property, is_new).
    Mutates session (add/flush); caller must commit.
    """
    # Stage 1a: exact match by (source_id, external_code) via existing offer
    existing_offer = (
        session.query(PropertyOffer)
        .filter_by(source_id=source_row.id, external_code=ext_code)
        .first()
    )
    if existing_offer:
        prop = session.get(Property, existing_offer.property_id)
        if prop:
            _upsert_offer(session, prop.id, source_row.id, normalized, ext_code)
            _refresh_best_price(session, prop.id)
            logger.info("dedup.exact_offer_match", source=source_row.code, ext_code=ext_code, property_id=str(prop.id))
            return prop, False

    # Stage 1b: backward compat — exact by (bank_id, external_code)
    existing_prop = (
        session.query(Property)
        .filter_by(bank_id=source_row.id, external_code=ext_code)
        .first()
    )
    if existing_prop:
        _upsert_offer(session, existing_prop.id, source_row.id, normalized, ext_code)
        _refresh_best_price(session, existing_prop.id)
        logger.info("dedup.exact_prop_match", source=source_row.code, ext_code=ext_code, property_id=str(existing_prop.id))
        return existing_prop, False

    # Stage 2: proximity + title similarity (only when we have coordinates + title)
    lat = normalized.get("latitude")
    lng = normalized.get("longitude")
    title = normalized.get("title")

    if lat and lng and title:
        geo_key = _geo_key(lat, lng)
        candidates = (
            session.query(Property)
            .filter_by(state=normalized.get("state"), city=normalized.get("city"))
            .filter(Property.latitude.isnot(None), Property.longitude.isnot(None))
            .all()
        )
        for cand in candidates:
            if _geo_key(cand.latitude, cand.longitude) == geo_key:
                sim = _title_sim(title, cand.title)
                if sim >= trgm_threshold:
                    _upsert_offer(session, cand.id, source_row.id, normalized, ext_code)
                    _refresh_best_price(session, cand.id)
                    logger.info(
                        "dedup.geo_title_match",
                        source=source_row.code,
                        ext_code=ext_code,
                        property_id=str(cand.id),
                        sim=round(sim, 3),
                    )
                    return cand, False
                elif sim >= TRGM_AMBIGUOUS_FLOOR:
                    prop = _create_property(session, normalized, source_row, ext_code)
                    prop.possible_duplicate_of = cand.id
                    _upsert_offer(session, prop.id, source_row.id, normalized, ext_code)
                    _refresh_best_price(session, prop.id)
                    logger.warning(
                        "dedup.flagged",
                        source=source_row.code,
                        ext_code=ext_code,
                        property_id=str(prop.id),
                        candidate_id=str(cand.id),
                        sim=round(sim, 3),
                    )
                    return prop, True

    # Stage 3: no match → new property + offer
    prop = _create_property(session, normalized, source_row, ext_code)
    _upsert_offer(session, prop.id, source_row.id, normalized, ext_code)
    _refresh_best_price(session, prop.id)
    logger.info("dedup.new_property", source=source_row.code, ext_code=ext_code, property_id=str(prop.id))
    return prop, True
