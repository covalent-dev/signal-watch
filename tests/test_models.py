"""Tests for Pydantic models."""

import pytest
from datetime import datetime
from src.models import (
    ChannelCreate,
    ChannelResponse,
    VideoResponse,
    DigestVideo,
    DigestResponse,
    HealthResponse,
)


class TestChannelModels:
    """Tests for channel models."""

    def test_channel_create_minimal(self):
        """Test ChannelCreate with minimal fields."""
        channel = ChannelCreate(id="test123", name="Test Channel")
        assert channel.id == "test123"
        assert channel.name == "Test Channel"
        assert channel.domain == "ai"
        assert channel.priority == 10

    def test_channel_create_full(self):
        """Test ChannelCreate with all fields."""
        channel = ChannelCreate(
            id="test123",
            name="Test Channel",
            url="https://youtube.com/@test",
            domain="tech",
            priority=5,
        )
        assert channel.url == "https://youtube.com/@test"
        assert channel.domain == "tech"
        assert channel.priority == 5


class TestVideoModels:
    """Tests for video models."""

    def test_video_response(self):
        """Test VideoResponse creation."""
        video = VideoResponse(
            id="vid123",
            channel_id="ch456",
            title="Test Video",
            url="https://youtube.com/watch?v=vid123",
            status="pending",
            created_at=datetime.utcnow(),
        )
        assert video.id == "vid123"
        assert video.channel_name is None


class TestDigestModels:
    """Tests for digest models."""

    def test_digest_video(self):
        """Test DigestVideo creation."""
        video = DigestVideo(
            title="Test Video",
            link="https://youtube.com/watch?v=test",
            channel="Test Channel",
            summary="This is a test summary.",
            key_points=["Point 1", "Point 2"],
        )
        assert len(video.key_points) == 2
        assert video.category == "ai"

    def test_digest_response(self):
        """Test DigestResponse creation."""
        digest = DigestResponse(
            generated_at=datetime.utcnow(),
            date="2025-01-23",
            videos=[],
        )
        assert digest.source == "signal-watch"
        assert len(digest.videos) == 0


class TestHealthResponse:
    """Tests for health response model."""

    def test_health_response(self):
        """Test HealthResponse creation."""
        health = HealthResponse(
            status="healthy",
            version="1.0.0",
            database="ok",
            ollama="ok",
        )
        assert health.status == "healthy"
