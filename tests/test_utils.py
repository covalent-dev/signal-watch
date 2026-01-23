"""Tests for utility functions."""

import pytest
from src.utils import (
    format_duration,
    truncate_text,
    youtube_video_url,
    youtube_channel_url,
)


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_none(self):
        """Test None input."""
        assert format_duration(None) == "Unknown"

    def test_seconds_only(self):
        """Test duration less than a minute."""
        assert format_duration(45) == "45s"

    def test_minutes_and_seconds(self):
        """Test duration with minutes and seconds."""
        assert format_duration(125) == "2m 5s"

    def test_hours_and_minutes(self):
        """Test duration with hours."""
        assert format_duration(3725) == "1h 2m"


class TestTruncateText:
    """Tests for truncate_text function."""

    def test_short_text(self):
        """Test text shorter than max length."""
        result = truncate_text("Hello", 100)
        assert result == "Hello"

    def test_long_text(self):
        """Test text longer than max length."""
        result = truncate_text("Hello World!", 8)
        assert result == "Hello..."
        assert len(result) == 8

    def test_exact_length(self):
        """Test text exactly at max length."""
        result = truncate_text("Hello", 5)
        assert result == "Hello"


class TestYouTubeUrls:
    """Tests for YouTube URL generation."""

    def test_video_url(self):
        """Test video URL generation."""
        url = youtube_video_url("dQw4w9WgXcQ")
        assert url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_channel_url(self):
        """Test channel URL generation."""
        url = youtube_channel_url("UC_x5XG1OV2P6uZZ5FSM9Ttw")
        assert url == "https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw"
