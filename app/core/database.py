import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import get_settings


def _make_engine():
    instance = os.getenv("CLOUD_SQL_INSTANCE", "")
    if instance:
        # Cloud Run: pg8000 doesn't support Unix sockets, use Cloud SQL connector
        from google.cloud.sql.connector import Connector

        _connector = Connector()

        def _getconn():
            return _connector.connect(
                instance,
                "pg8000",
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", ""),
                db=os.getenv("DB_NAME", "radar"),
            )

        return create_engine(
            "postgresql+pg8000://",
            creator=_getconn,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )

    # Local dev: use DATABASE_URL directly (e.g. postgresql+pg8000:// or postgresql://)
    return create_engine(
        get_settings().database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )


engine = _make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
