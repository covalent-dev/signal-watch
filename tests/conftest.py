"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
import tempfile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_video_info():
    """Create sample VideoInfo for testing."""
    from src.sources.youtube import VideoInfo
    from datetime import datetime

    return VideoInfo(
        id="test_video_123",
        channel_id="test_channel_456",
        title="Test Video Title",
        url="https://www.youtube.com/watch?v=test_video_123",
        published_at=datetime.utcnow(),
        duration_seconds=300,
    )
