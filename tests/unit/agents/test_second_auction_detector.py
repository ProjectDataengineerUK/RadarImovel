"""Tests for SecondAuctionDetector."""
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest
from app.agents.second_auction_detector import SecondAuctionDetector, _SEGUNDA_PRACA_THRESHOLD


@pytest.fixture
def detector():
    return SecondAuctionDetector()


@pytest.fixture
def mock_session():
    session = MagicMock()
    prop = MagicMock()
    prop.auction_stage = "primeira_praca"
    session.query.return_value.filter_by.return_value.first.return_value = prop
    return session, prop


def test_detect_returns_true_on_40pct_drop(detector, mock_session):
    session, prop = mock_session
    result = detector.detect(
        property_id="some-uuid",
        old_minimum=Decimal("100000"),
        new_minimum=Decimal("60000"),
        old_stage="primeira_praca",
        session=session,
    )
    assert result is True


def test_detect_returns_false_below_threshold(detector, mock_session):
    session, _ = mock_session
    result = detector.detect(
        property_id="some-uuid",
        old_minimum=Decimal("100000"),
        new_minimum=Decimal("75000"),
        old_stage="primeira_praca",
        session=session,
    )
    assert result is False


def test_detect_exactly_threshold_qualifies(detector, mock_session):
    session, _ = mock_session
    result = detector.detect(
        property_id="some-uuid",
        old_minimum=Decimal("100000"),
        new_minimum=Decimal("60000"),
        old_stage=None,
        session=session,
    )
    assert result is True


def test_detect_already_segunda_praca_skips(detector, mock_session):
    session, _ = mock_session
    result = detector.detect(
        property_id="some-uuid",
        old_minimum=Decimal("100000"),
        new_minimum=Decimal("50000"),
        old_stage="segunda_praca",
        session=session,
    )
    assert result is False


def test_detect_zero_old_value_skips(detector, mock_session):
    session, _ = mock_session
    result = detector.detect(
        property_id="some-uuid",
        old_minimum=Decimal("0"),
        new_minimum=Decimal("50000"),
        old_stage=None,
        session=session,
    )
    assert result is False
