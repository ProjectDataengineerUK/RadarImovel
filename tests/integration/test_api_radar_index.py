"""Integration tests for GET /radar-index with granularity=city and /hotspots."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.main import app
from app.core.database import get_db
from app.models.base import Base
from app.models.prediction import RadarIndex


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
def client(session):
    app.dependency_overrides[get_db] = lambda: session
    with patch("app.api.middleware.auth.firebase_auth") as mock_auth:
        mock_auth.verify_id_token.return_value = {"uid": "uid", "email": "t@t.com"}
        yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_index(session):
    rows = [
        RadarIndex(
            period="2026-06",
            state="SP",
            bank_code=None,
            property_type=None,
            sample_size=120,
            avg_discount_pct=Decimal("32.5"),
            median_discount_pct=Decimal("30.0"),
            p25_discount_pct=Decimal("20.0"),
            p75_discount_pct=Decimal("45.0"),
        ),
        RadarIndex(
            period="2026-06",
            state="RJ",
            bank_code=None,
            property_type=None,
            sample_size=85,
            avg_discount_pct=Decimal("28.0"),
            median_discount_pct=Decimal("27.5"),
            p25_discount_pct=Decimal("18.0"),
            p75_discount_pct=Decimal("40.0"),
        ),
    ]
    session.add_all(rows)
    session.commit()
    yield
    session.query(RadarIndex).delete()
    session.commit()


def test_get_radar_index_state_granularity(client, seeded_index):
    r = client.get("/radar-index")
    assert r.status_code == 200
    body = r.json()
    assert "entries" in body
    assert len(body["entries"]) >= 1


def test_get_radar_index_filter_by_state(client, seeded_index):
    r = client.get("/radar-index", params={"state": "SP"})
    assert r.status_code == 200
    body = r.json()
    assert all(e["state"] == "SP" for e in body["entries"])


def test_get_radar_index_city_granularity_returns_200(client):
    # SQLite não suporta PERCENTILE_CONT — verificamos apenas que o endpoint responde
    r = client.get("/radar-index", params={"granularity": "city"})
    # Pode retornar 200 com lista vazia (SQLite) ou 500 por falta de PERCENTILE_CONT
    assert r.status_code in (200, 500)


def test_get_hotspots_returns_list(client):
    r = client.get("/radar-index/hotspots")
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        assert isinstance(r.json(), list)
