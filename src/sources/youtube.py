"""YouTube channel polling and video discovery."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import feedparser
import httpx
from dateutil import parser as date_parser

from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class VideoInfo:
    """Information about a discovered video."""
    id: str
    channel_id: str
    title: str
    url: str
    published_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None


class YouTubeSource:
    """YouTube channel polling via RSS feeds."""

    RSS_BASE = "https://www.youtube.com/feeds/videos.xml"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def get_channel_feed_url(self, channel_id: str) -> str:
        """Get RSS feed URL for a channel."""
        return f"{self.RSS_BASE}?channel_id={channel_id}"

    def poll_channel(self, channel_id: str, max_videos: int = 10) -> list[VideoInfo]:
        """
        Poll a YouTube channel's RSS feed for recent videos.

        Args:
            channel_id: YouTube channel ID
            max_videos: Maximum number of videos to return

        Returns:
            List of VideoInfo objects for discovered videos
        """
        feed_url = self.get_channel_feed_url(channel_id)
        logger.debug(f"Polling channel feed: {feed_url}")

        try:
            response = self.client.get(feed_url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch channel feed {channel_id}: {e}")
            return []

        feed = feedparser.parse(response.text)

        if not feed.entries:
            logger.info(f"No videos found for channel {channel_id}")
            return []

        videos = []
        for entry in feed.entries[:max_videos]:
            video = self._parse_entry(entry, channel_id)
            if video:
                videos.append(video)

        logger.info(f"Found {len(videos)} videos for channel {channel_id}")
        return videos

    def _parse_entry(self, entry: dict, channel_id: str) -> Optional[VideoInfo]:
        """Parse a feed entry into VideoInfo."""
        try:
            video_id = entry.get("yt_videoid") or self._extract_video_id(entry.get("link", ""))
            if not video_id:
                return None

            published_at = None
            if entry.get("published"):
                try:
                    published_at = date_parser.parse(entry["published"])
                except (ValueError, TypeError):
                    pass

            return VideoInfo(
                id=video_id,
                channel_id=channel_id,
                title=entry.get("title", "Unknown Title"),
                url=f"https://www.youtube.com/watch?v={video_id}",
                published_at=published_at,
                duration_seconds=None,  # RSS doesn't include duration
            )
        except Exception as e:
            logger.warning(f"Failed to parse feed entry: {e}")
            return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        patterns = [
            r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
            r"(?:embed/)([a-zA-Z0-9_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
