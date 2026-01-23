"""Tests for YouTube source."""

import pytest
from src.sources.youtube import YouTubeSource, VideoInfo


class TestYouTubeSource:
    """Tests for YouTubeSource class."""

    def test_get_channel_feed_url(self):
        """Test RSS feed URL generation."""
        source = YouTubeSource()
        url = source.get_channel_feed_url("UC_x5XG1OV2P6uZZ5FSM9Ttw")
        assert "channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw" in url
        assert url.startswith("https://www.youtube.com/feeds/videos.xml")

    def test_extract_video_id_standard(self):
        """Test video ID extraction from standard URL."""
        source = YouTubeSource()
        video_id = source._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_short(self):
        """Test video ID extraction from short URL."""
        source = YouTubeSource()
        video_id = source._extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_embed(self):
        """Test video ID extraction from embed URL."""
        source = YouTubeSource()
        video_id = source._extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid(self):
        """Test video ID extraction from invalid URL."""
        source = YouTubeSource()
        video_id = source._extract_video_id("https://example.com/")
        assert video_id is None


class TestVideoInfo:
    """Tests for VideoInfo dataclass."""

    def test_video_info_creation(self):
        """Test VideoInfo creation."""
        video = VideoInfo(
            id="test123",
            channel_id="channel456",
            title="Test Video",
            url="https://youtube.com/watch?v=test123",
        )
        assert video.id == "test123"
        assert video.channel_id == "channel456"
        assert video.published_at is None
        assert video.duration_seconds is None
