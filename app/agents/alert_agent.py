import asyncio
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.config import get_settings
from app.core.logging import logger
from app.models.property import Property
from app.models.user import User, Watchlist, Alert
from app.services.notification import TelegramChannel
from app.services.telegram import format_property_alert

settings = get_settings()


def match_watchlists(session: Session, property_id: str) -> list[tuple[User, Watchlist]]:
    prop = session.query(Property).filter_by(id=property_id).first()
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
        if user and user.telegram_chat_id:
            matches.append((user, wl))

    return matches


async def process_property_event(event: dict) -> None:
    property_id = event.get("property_id")
    event_type = event.get("event_type")

    if not property_id:
        logger.warning("alert_agent.missing_property_id", event=event)
        return

    channel = TelegramChannel(token=settings.telegram_bot_token)

    with SessionLocal() as session:
        matches = match_watchlists(session, property_id)
        prop = session.query(Property).filter_by(id=property_id).first()

        for user, watchlist in matches:
            message = format_property_alert({
                "city": prop.city,
                "state": prop.state,
                "current_value": prop.current_value,
                "discount_percent": prop.discount_percent,
                "sale_modality": prop.sale_modality,
                "occupancy_status": prop.occupancy_status,
                "opportunity_score": prop.opportunity_score,
                "official_url": prop.official_url,
            })

            success = False
            for attempt in range(1, settings.alert_max_retries + 1):
                success = await channel.send(str(user.telegram_chat_id), message)
                if success:
                    break
                logger.warning("alert_agent.retry", user_id=str(user.id), attempt=attempt)
                await asyncio.sleep(2 ** attempt)

            alert = Alert(
                user_id=user.id,
                property_id=prop.id,
                watchlist_id=watchlist.id,
                channel="telegram",
                status="success" if success else "failed",
                message=message,
                sent_at=datetime.now(timezone.utc) if success else None,
            )
            session.add(alert)

        session.commit()
        logger.info("alert_agent.processed", property_id=property_id, matches=len(matches))
