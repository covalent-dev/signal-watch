"""Transcript fetching and normalization."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from ..config import get_config, get_project_root
from ..utils import get_logger, save_text

logger = get_logger(__name__)


@dataclass
class TranscriptResult:
    """Result of transcript fetch operation."""
    video_id: str
    text: str
    source: str  # youtube_auto, youtube_manual
    language: str
    success: bool
    error: Optional[str] = None


class TranscriptFetcher:
    """Fetches and normalizes YouTube transcripts."""

    def __init__(self, save_to_file: bool = True):
        self.save_to_file = save_to_file
        self.config = get_config()
        self.transcripts_dir = get_project_root() / self.config.storage.transcripts_dir

    def fetch(self, video_id: str) -> TranscriptResult:
        """
        Fetch transcript for a YouTube video.

        Args:
            video_id: YouTube video ID

        Returns:
            TranscriptResult with transcript text or error
        """
        logger.debug(f"Fetching transcript for video: {video_id}")

        try:
            # Try to get available transcripts
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Prefer manual transcripts, fall back to auto-generated
            transcript = None
            source = "youtube_auto"

            try:
                transcript = transcript_list.find_manually_created_transcript(["en"])
                source = "youtube_manual"
            except NoTranscriptFound:
                try:
                    transcript = transcript_list.find_generated_transcript(["en"])
                except NoTranscriptFound:
                    # Try any available transcript
                    for t in transcript_list:
                        transcript = t
                        source = "youtube_manual" if not t.is_generated else "youtube_auto"
                        break

            if transcript is None:
                return TranscriptResult(
                    video_id=video_id,
                    text="",
                    source="",
                    language="",
                    success=False,
                    error="No transcript available"
                )

            # Fetch the actual transcript content
            transcript_data = transcript.fetch()
            text = self._normalize_transcript(transcript_data)
            language = transcript.language_code

            # Optionally save to file
            if self.save_to_file and text:
                self._save_transcript(video_id, text)

            logger.info(f"Fetched transcript for {video_id}: {len(text)} chars")

            return TranscriptResult(
                video_id=video_id,
                text=text,
                source=source,
                language=language,
                success=True
            )

        except TranscriptsDisabled:
            logger.warning(f"Transcripts disabled for video: {video_id}")
            return TranscriptResult(
                video_id=video_id,
                text="",
                source="",
                language="",
                success=False,
                error="Transcripts disabled"
            )
        except VideoUnavailable:
            logger.warning(f"Video unavailable: {video_id}")
            return TranscriptResult(
                video_id=video_id,
                text="",
                source="",
                language="",
                success=False,
                error="Video unavailable"
            )
        except Exception as e:
            logger.error(f"Failed to fetch transcript for {video_id}: {e}")
            return TranscriptResult(
                video_id=video_id,
                text="",
                source="",
                language="",
                success=False,
                error=str(e)
            )

    def _normalize_transcript(self, transcript_data: list[dict]) -> str:
        """
        Normalize transcript data into clean text.

        Args:
            transcript_data: List of transcript segments from YouTube API

        Returns:
            Normalized text string
        """
        # Extract text from segments
        segments = [item.get("text", "") for item in transcript_data]
        text = " ".join(segments)

        # Clean up the text
        text = re.sub(r"\s+", " ", text)  # Normalize whitespace
        text = re.sub(r"\[.*?\]", "", text)  # Remove [Music], [Applause], etc.
        text = text.strip()

        return text

    def _save_transcript(self, video_id: str, text: str) -> None:
        """Save transcript to file."""
        filepath = self.transcripts_dir / f"{video_id}.txt"
        save_text(text, filepath)
        logger.debug(f"Saved transcript to {filepath}")
