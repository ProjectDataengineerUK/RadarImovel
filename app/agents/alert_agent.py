import asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.config import get_settings
from app.core.logging import logger
from app.models.property import Property
from app.models.user import User, Watchlist, Alert
from app.services.notification import build_channels
from app.services.telegram import format_property_alert

settings = get_settings()


def match_watchlists(session: Session, property_id: str) -> list[tuple[User, Watchlist]]:
    prop = session.query(Property).filter_by(id=uuid.UUID(property_id)).first()
    if not prop:
        return []

    watchlists = (
        session.query(Watchlist)
        .filter(Watchlist.active == True)  # noqa: E712
        .all()
    )

    matches = []
    for wl in watchlists:
        if wl.state and wl.state.upper() != prop.state.upper():
            continue
        if wl.city and wl.city.lower() not in prop.city.lower():
            continue
        if wl.max_price and prop.current_value > wl.max_price:
            continue
        if wl.min_discount and (prop.discount_percent or 0) < wl.min_discount:
            continue
        if wl.property_type and wl.property_type.lower() not in prop.property_type.lower():
            continue

        user = session.query(User).filter_by(id=wl.user_id).first()
        if user and (user.telegram_chat_id or user.notification_channels):
            matches.append((user, wl))

    return matches


def _latency_minutes(prop: Property) -> int | None:
    if not prop.first_seen_at:
        return None
    now = datetime.now(timezone.utc)
    first = prop.first_seen_at
    if first.tzinfo is None:
        first = first.replace(tzinfo=timezone.utc)
    return max(0, int((now - first).total_seconds() / 60))


async def _send_to_user(user: User, prop: Property, watchlist: Watchlist, session: Session) -> None:
    message = format_property_alert({
        "city": prop.city,
        "state": prop.state,
        "current_value": prop.current_value,
        "discount_percent": prop.discount_percent,
        "sale_modality": prop.sale_modality,
        "occupancy_status": prop.occupancy_status,
        "opportunity_score": prop.opportunity_score,
        "official_url": prop.official_url,
        "detected_latency_min": _latency_minutes(prop),
    })

    channels = build_channels(user)
    if not channels:
        return

    for channel, dest in channels:
        success = False
        channel_name = type(channel).__name__.lower().replace("channel", "")
        for attempt in range(1, settings.alert_max_retries + 1):
            success = await channel.send(dest, message)
            if success:
                break
            logger.warning("alert_agent.retry", user_id=str(user.id), channel=channel_name, attempt=attempt)
            await asyncio.sleep(2 ** attempt)

        alert = Alert(
            user_id=user.id,
            property_id=prop.id,
            watchlist_id=watchlist.id,
            channel=channel_name,
            status="success" if success else "failed",
            message=message,
            sent_at=datetime.now(timezone.utc) if success else None,
        )
        session.add(alert)


async def process_property_event(event: dict) -> None:
    property_id = event.get("property_id")

    if not property_id:
        logger.warning("alert_agent.missing_property_id", event=event)
        return

    with SessionLocal() as session:
        matches = match_watchlists(session, property_id)
        prop = session.query(Property).filter_by(id=uuid.UUID(property_id)).first()

        for user, watchlist in matches:
            await _send_to_user(user, prop, watchlist, session)

        session.commit()
        logger.info("alert_agent.processed", property_id=property_id, matches=len(matches))
