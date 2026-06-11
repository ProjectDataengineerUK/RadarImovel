"""Integration tests for calculate_risk job: event → score persisted → risk-change published."""
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest


def _make_prop(prop_id=None):
    prop = MagicMock()
    prop.id = prop_id or uuid.uuid4()
    prop.address = "Rua Teste, 123"
    prop.city = "São Paulo"
    prop.state = "SP"
    prop.latitude = -23.55
    prop.longitude = -46.60
    prop.occupancy_status = "livre"
    prop.current_value = 300_000
    prop.area_total = 100
    prop.appraisal_value = 400_000
    prop.zipcode = "01310-100"
    prop.ibge_code = None
    prop.edital_url = None
    return prop


def _mock_all_sources(score_value: float = 0.0):
    """Patch all external sources to return neutral values."""
    return [
        patch("app.risk.calculator.CnjClient", return_value=MagicMock(search=MagicMock(return_value=[]))),
        patch("app.risk.calculator.IbamaLookup", return_value=MagicMock(contains_point=MagicMock(return_value=[]))),
        patch("app.risk.calculator.CemadenLookup", return_value=MagicMock(risk_zones=MagicMock(return_value=[]))),
        patch("app.risk.calculator.TransparenciaClient", return_value=MagicMock(get_iptu_debt=MagicMock(return_value=None))),
        patch("app.risk.calculator.IbgeLookup", return_value=MagicMock(get_stats=MagicMock(return_value=None))),
        patch("app.risk.calculator.IpeaAtlas", return_value=MagicMock(get_homicide_rate=MagicMock(return_value=None))),
        patch("app.risk.calculator.ReceitaClient", return_value=MagicMock(get_cnpj=MagicMock(return_value=None))),
        patch("app.risk.calculator.FipeClient", return_value=MagicMock(get_price_per_sqm=MagicMock(return_value=None))),
    ]


def test_new_property_creates_risk_score():
    """First event for a property → PropertyRiskScore created, no risk-change published."""
    from jobs.calculate_risk import process_message

    prop_id = uuid.uuid4()
    prop = _make_prop(prop_id)

    session = MagicMock()
    session.query.return_value.filter_by.return_value.first.side_effect = [prop, None]  # prop found, no prev score

    with patch("jobs.calculate_risk.publish_event") as mock_pub:
        patches = _mock_all_sources()
        for p in patches:
            p.start()
        try:
            result = process_message(session, {"property_id": str(prop_id)})
        finally:
            for p in patches:
                p.stop()

    assert result == "done"
    session.add.assert_called_once()
    mock_pub.assert_not_called()  # no previous score → no change event


def test_updated_property_publishes_risk_change_when_score_changes():
    """When score changes > threshold, risk-change-event is published."""
    from jobs.calculate_risk import process_message

    prop_id = uuid.uuid4()
    prop = _make_prop(prop_id)

    prev_score = MagicMock()
    prev_score.score_total = 80.0
    prev_score.risk_level = "high"

    session = MagicMock()
    session.query.return_value.filter_by.return_value.first.side_effect = [prop, prev_score]

    with patch("jobs.calculate_risk.publish_event") as mock_pub:
        patches = _mock_all_sources()
        for p in patches:
            p.start()
        try:
            result = process_message(session, {"property_id": str(prop_id)})
        finally:
            for p in patches:
                p.stop()

    assert result == "done"
    # score went from 80 → 0, delta = 80 > threshold(10) → should publish
    mock_pub.assert_called_once()
    event = mock_pub.call_args[0][1]
    assert event["old_score"] == 80.0
    assert event["new_level"] == "low"


def test_property_not_found_returns_ignored():
    """If property_id not found in DB, return 'ignored'."""
    from jobs.calculate_risk import process_message

    session = MagicMock()
    session.query.return_value.filter_by.return_value.first.return_value = None

    result = process_message(session, {"property_id": str(uuid.uuid4())})
    assert result == "ignored"
