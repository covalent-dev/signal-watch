"""Database connection and session management."""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from .config import get_config, get_project_root
from .models import Base


def get_database_url() -> str:
    """Get the database URL from config."""
    config = get_config()
    db_path = get_project_root() / config.storage.database
    return f"sqlite:///{db_path}"


def create_db_engine(database_url: str | None = None):
    """Create the database engine."""
    url = database_url or get_database_url()
    engine = create_engine(url, echo=False)

    # Enable foreign keys for SQLite
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


# Global engine and session factory
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


def get_session_factory():
    """Get or create the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


def init_db():
    """Initialize the database and create tables."""
    config = get_config()
    db_path = get_project_root() / config.storage.database

    # Ensure data directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create all tables
    engine = get_engine()
    Base.metadata.create_all(engine)

    return engine


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting a database session."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
