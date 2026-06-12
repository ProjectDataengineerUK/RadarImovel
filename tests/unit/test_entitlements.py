"""Testes unitários do módulo entitlements: catálogo, has_feature, consume, cache."""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.entitlements.catalog import FEATURES, QUOTAS, validate_plan_config
from app.entitlements.service import Entitlements, get_entitlements, has_feature, invalidate_cache
from app.models.base import Base
from app.models.plan import Plan, Subscription, UsageCounter
from app.models.user import User


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def free_plan(db):
    plan = Plan(
        code="free",
        name="Free",
        price_brl=0,
        features={k: False for k in FEATURES},
        limits={"alerts_per_day": 5, "watchlists": 2},
    )
    db.add(plan)
    db.flush()
    return plan


@pytest.fixture
def pro_plan(db):
    plan = Plan(
        code="pro",
        name="Pro",
        price_brl=7900,
        features={"risk_score": True, "export": True, "calculator": True,
                  "portfolio": True, "realtime_alerts": True},
        limits={"alerts_per_day": 50, "watchlists": 10},
    )
    db.add(plan)
    db.flush()
    return plan


@pytest.fixture
def user_with_pro(db, pro_plan):
    user = User(firebase_uid=f"uid_{uuid.uuid4().hex}", email="pro@test.com")
    db.add(user)
    db.flush()
    sub = Subscription(user_id=user.id, plan_id=pro_plan.id)
    db.add(sub)
    db.flush()
    user.subscription_id = sub.id
    db.flush()
    invalidate_cache(str(user.id))
    return user


@pytest.fixture
def user_free(db, free_plan):
    user = User(firebase_uid=f"uid_{uuid.uuid4().hex}", email="free@test.com")
    db.add(user)
    db.flush()
    sub = Subscription(user_id=user.id, plan_id=free_plan.id)
    db.add(sub)
    db.flush()
    user.subscription_id = sub.id
    db.flush()
    invalidate_cache(str(user.id))
    return user


# ── Catálogo ───────────────────────────────────────────────────────────────────

def test_catalog_has_expected_features():
    assert "risk_score" in FEATURES
    assert "export" in FEATURES
    assert "ask" in FEATURES


def test_validate_plan_config_valid():
    errors = validate_plan_config({"risk_score": True, "export": False}, {"alerts_per_day": 10})
    assert errors == []


def test_validate_plan_config_unknown_feature():
    errors = validate_plan_config({"nonexistent_flag": True}, {})
    assert any("nonexistent_flag" in e for e in errors)


def test_validate_plan_config_unknown_quota():
    errors = validate_plan_config({}, {"unknown_quota": 5})
    assert any("unknown_quota" in e for e in errors)


# ── has_feature ────────────────────────────────────────────────────────────────

def test_has_feature_pro_plan(db, user_with_pro):
    assert has_feature(db, user_with_pro, "risk_score") is True
    assert has_feature(db, user_with_pro, "export") is True


def test_has_feature_free_plan_returns_false(db, user_free):
    assert has_feature(db, user_free, "risk_score") is False
    assert has_feature(db, user_free, "ask") is False


def test_has_feature_unknown_flag_returns_false(db, user_with_pro):
    assert has_feature(db, user_with_pro, "nonexistent_feature") is False


def test_has_feature_no_subscription(db):
    user = User(firebase_uid=f"uid_{uuid.uuid4().hex}", email="nosub@test.com")
    db.add(user)
    db.flush()
    invalidate_cache(str(user.id))
    assert has_feature(db, user, "risk_score") is False


# ── get_entitlements / cache ───────────────────────────────────────────────────

def test_get_entitlements_returns_correct_plan(db, user_with_pro):
    ent = get_entitlements(db, user_with_pro)
    assert ent.plan_code == "pro"
    assert ent.features.get("risk_score") is True


def test_entitlements_cache_hit(db, user_with_pro):
    invalidate_cache(str(user_with_pro.id))
    ent1 = get_entitlements(db, user_with_pro)
    ent2 = get_entitlements(db, user_with_pro)
    assert ent1 is ent2  # mesmo objeto = cache hit


def test_invalidate_cache_forces_reload(db, user_with_pro):
    ent1 = get_entitlements(db, user_with_pro)
    invalidate_cache(str(user_with_pro.id))
    ent2 = get_entitlements(db, user_with_pro)
    # Mesmos dados mas objeto diferente (recarregado)
    assert ent1.plan_code == ent2.plan_code
    assert ent1 is not ent2


# ── consume ────────────────────────────────────────────────────────────────────

def test_consume_within_limit(db, user_free):
    """5 alertas/dia — primeiros 5 devem passar."""
    from app.entitlements.service import consume
    invalidate_cache(str(user_free.id))
    # Consome do SQLite — ON CONFLICT suportado em SQLite 3.24+
    for _ in range(5):
        assert consume(db, user_free, "alerts_per_day", "day") is True


def test_consume_exceeds_limit(db, user_free):
    """6º consumo deve falhar (limite=5)."""
    from app.entitlements.service import consume, _period_key
    from sqlalchemy import text

    # Força contador já em 5
    pk = _period_key("day")
    db.execute(text("""
        INSERT OR REPLACE INTO usage_counters (id, user_id, feature, period_key, count)
        VALUES (lower(hex(randomblob(16))), :uid, :feat, :pk, 5)
    """), {"uid": str(user_free.id), "feat": "alerts_per_day", "pk": pk})
    db.flush()

    result = consume(db, user_free, "alerts_per_day", "day")
    assert result is False


def test_consume_unlimited_when_no_limit_defined(db, user_with_pro):
    """Features sem limite no plano = ilimitado."""
    from app.entitlements.service import consume
    invalidate_cache(str(user_with_pro.id))
    # Pro plan não tem "ask_per_day" no limite = ilimitado
    assert consume(db, user_with_pro, "ask_per_day", "day") is True
