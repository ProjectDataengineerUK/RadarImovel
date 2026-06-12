"""Testes unitários do helper audit()."""
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.entitlements.audit import audit
from app.models.base import Base
from app.models.plan import AuditLog
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
def actor(db):
    user = User(firebase_uid=f"uid_{uuid.uuid4().hex}", email="admin@test.com", role="admin")
    db.add(user)
    db.flush()
    return user


def test_audit_creates_entry(db, actor):
    before = {"name": "Free"}
    after = {"name": "Free v2"}

    entry = audit(db, actor, "plan.update", "plan", "some-plan-id", before=before, after=after)

    assert entry.id is not None
    assert entry.actor_user_id == actor.id
    assert entry.action == "plan.update"
    assert entry.entity_type == "plan"
    assert entry.entity_id == "some-plan-id"
    assert entry.before == before
    assert entry.after == after


def test_audit_without_before_after(db, actor):
    entry = audit(db, actor, "plan.create", "plan", "new-id")
    assert entry.before is None
    assert entry.after is None


def test_audit_persists_to_db(db, actor):
    audit(db, actor, "user.set_role", "user", str(actor.id),
          before={"role": "user"}, after={"role": "operador"})
    db.commit()

    found = db.query(AuditLog).filter_by(action="user.set_role", entity_id=str(actor.id)).first()
    assert found is not None
    assert found.before == {"role": "user"}
    assert found.after == {"role": "operador"}


def test_audit_requires_actor(db):
    with pytest.raises(Exception):
        # actor_user_id é NOT NULL — deve falhar
        entry = AuditLog(
            actor_user_id=None,
            action="plan.delete",
            entity_type="plan",
            entity_id="x",
        )
        db.add(entry)
        db.flush()
