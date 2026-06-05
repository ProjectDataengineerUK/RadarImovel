import uuid
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.bank import Bank
from app.models.property import Property
from app.models.user import User, Watchlist, Alert
from app.agents.alert_agent import match_watchlists, process_property_event


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
def session(engine):
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.rollback()
    s.close()


@pytest.fixture
def seed(session):
    bank = Bank(id=uuid.uuid4(), code="caixa", name="Caixa Econômica Federal")
    session.add(bank)

    prop = Property(
        id=uuid.uuid4(), bank_id=bank.id, external_code="EXT1",
        property_type="Apartamento", city="Goiânia", state="GO",
        minimum_value=Decimal("100000"), current_value=Decimal("200000"),
        discount_percent=Decimal("25"), occupancy_status="Desocupado",
        sale_modality="Licitação Aberta",
        official_url="https://example.com/1",
        status="active", content_hash="h" * 64,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    session.add(prop)

    user = User(
        id=uuid.uuid4(), firebase_uid="firebase-uid-1",
        email="test@test.com", telegram_chat_id=123456789,
        created_at=datetime.now(timezone.utc),
    )
    session.add(user)

    wl_match = Watchlist(
        id=uuid.uuid4(), user_id=user.id,
        state="GO", city=None, max_price=None,
        min_discount=None, property_type=None, active=True,
        created_at=datetime.now(timezone.utc),
    )
    wl_no_match = Watchlist(
        id=uuid.uuid4(), user_id=user.id,
        state="SP", city=None, max_price=None,
        min_discount=None, property_type=None, active=True,
        created_at=datetime.now(timezone.utc),
    )
    session.add_all([wl_match, wl_no_match])
    session.flush()

    return {"bank": bank, "prop": prop, "user": user, "wl_match": wl_match, "wl_no_match": wl_no_match}


def test_match_by_state(session, seed):
    matches = match_watchlists(session, str(seed["prop"].id))
    assert len(matches) == 1
    assert matches[0][1].id == seed["wl_match"].id


def test_no_match_different_state(session, seed):
    wl = Watchlist(
        id=uuid.uuid4(), user_id=seed["user"].id,
        state="RJ", active=True,
        created_at=datetime.now(timezone.utc),
    )
    session.add(wl)
    session.flush()
    matches = match_watchlists(session, str(seed["prop"].id))
    assert not any(m[1].id == wl.id for m in matches)


def test_match_respects_max_price(session, seed):
    wl = Watchlist(
        id=uuid.uuid4(), user_id=seed["user"].id,
        state="GO", max_price=Decimal("100000"), active=True,
        created_at=datetime.now(timezone.utc),
    )
    session.add(wl)
    session.flush()
    matches = match_watchlists(session, str(seed["prop"].id))
    assert not any(m[1].id == wl.id for m in matches)


def test_match_respects_min_discount(session, seed):
    wl = Watchlist(
        id=uuid.uuid4(), user_id=seed["user"].id,
        state="GO", min_discount=Decimal("50"), active=True,
        created_at=datetime.now(timezone.utc),
    )
    session.add(wl)
    session.flush()
    matches = match_watchlists(session, str(seed["prop"].id))
    assert not any(m[1].id == wl.id for m in matches)


def test_process_event_sends_telegram(seed):
    with patch("app.agents.alert_agent.SessionLocal") as mock_sl, \
         patch("app.agents.alert_agent.TelegramChannel") as mock_channel_cls, \
         patch("app.agents.alert_agent.match_watchlists") as mock_match, \
         patch("app.agents.alert_agent.format_property_alert", return_value="Alert!"):

        mock_channel = AsyncMock()
        mock_channel.send.return_value = True
        mock_channel_cls.return_value = mock_channel

        mock_session = MagicMock()
        mock_sl.return_value.__enter__.return_value = mock_session

        prop = MagicMock()
        prop.city = "Goiânia"
        prop.state = "GO"
        prop.current_value = Decimal("200000")
        prop.discount_percent = Decimal("25")
        prop.sale_modality = "Licitação Aberta"
        prop.occupancy_status = "Desocupado"
        prop.opportunity_score = 65
        prop.official_url = "https://example.com"
        mock_session.query.return_value.filter_by.return_value.first.return_value = prop

        user = MagicMock()
        user.telegram_chat_id = 123456789
        watchlist = MagicMock()
        mock_match.return_value = [(user, watchlist)]

        asyncio.run(process_property_event({"property_id": str(uuid.uuid4()), "event_type": "new"}))
        mock_channel.send.assert_called_once()
