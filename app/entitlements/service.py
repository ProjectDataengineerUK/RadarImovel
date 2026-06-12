from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.plan import Plan, Subscription
from app.models.user import User

_CACHE_TTL_S = 60
_cache: dict[str, tuple[float, "Entitlements"]] = {}


@dataclass
class Entitlements:
    plan_code: str
    features: dict[str, bool] = field(default_factory=dict)
    limits: dict[str, int] = field(default_factory=dict)


def get_entitlements(db: Session, user: User) -> Entitlements:
    cache_key = str(user.id)
    entry = _cache.get(cache_key)
    if entry and (time.monotonic() - entry[0]) < _CACHE_TTL_S:
        return entry[1]

    ent = _load_entitlements(db, user)
    _cache[cache_key] = (time.monotonic(), ent)
    return ent


def _load_entitlements(db: Session, user: User) -> Entitlements:
    if user.subscription_id is None:
        return Entitlements(plan_code="free")

    row = (
        db.query(Plan)
        .join(Subscription, Subscription.plan_id == Plan.id)
        .filter(Subscription.id == user.subscription_id)
        .first()
    )
    if row is None:
        return Entitlements(plan_code="free")

    return Entitlements(
        plan_code=row.code,
        features=row.features or {},
        limits=row.limits or {},
    )


def has_feature(db: Session, user: User, flag: str) -> bool:
    return get_entitlements(db, user).features.get(flag, False)


def consume(db: Session, user: User, feature: str, period: str) -> bool:
    limit = get_entitlements(db, user).limits.get(feature)
    if limit is None:
        return True  # sem limite definido = ilimitado

    period_key = _period_key(period)
    row = db.execute(
        text("""
            INSERT INTO usage_counters (id, user_id, feature, period_key, count)
            VALUES (:id, :uid, :feat, :pk, 1)
            ON CONFLICT (user_id, feature, period_key)
            DO UPDATE SET count = usage_counters.count + 1
            RETURNING count
        """),
        {"id": str(uuid.uuid4()), "uid": str(user.id), "feat": feature, "pk": period_key},
    ).one()
    return row.count <= limit


def invalidate_cache(user_id: str) -> None:
    _cache.pop(user_id, None)


def _period_key(period: str) -> str:
    now = datetime.now(timezone.utc)
    if period == "month":
        return now.strftime("%Y-%m")
    return now.strftime("%Y-%m-%d")
