"""Deduplication logic for videos."""

from sqlalchemy.orm import Session

from ..models import VideoORM
from ..utils import get_logger

logger = get_logger(__name__)


class Deduplicator:
    """Handles deduplication of videos by ID."""

    def __init__(self, session: Session):
        self.session = session

    def filter_new_videos(self, video_ids: list[str]) -> list[str]:
        """
        Filter out video IDs that already exist in the database.

        Args:
            video_ids: List of video IDs to check

        Returns:
            List of video IDs that don't exist in the database
        """
        if not video_ids:
            return []

        existing = self.session.query(VideoORM.id).filter(
            VideoORM.id.in_(video_ids)
        ).all()

        existing_ids = {row[0] for row in existing}
        new_ids = [vid for vid in video_ids if vid not in existing_ids]

        if existing_ids:
            logger.debug(f"Filtered out {len(existing_ids)} existing videos")

        return new_ids

    def is_duplicate(self, video_id: str) -> bool:
        """Check if a video ID already exists."""
        return self.session.query(VideoORM).filter(VideoORM.id == video_id).first() is not None
