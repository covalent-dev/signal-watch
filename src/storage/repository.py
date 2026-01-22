"""Repository for CRUD operations."""

import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ..models import (
    ChannelCreate,
    ChannelORM,
    RunORM,
    SummaryORM,
    TranscriptORM,
    VideoORM,
)
from ..sources.youtube import VideoInfo
from ..utils import get_logger

logger = get_logger(__name__)


class Repository:
    """Repository for database operations."""

    def __init__(self, session: Session):
        self.session = session

    # Channel operations
    def get_channels(self, active_only: bool = False) -> list[ChannelORM]:
        """Get all channels."""
        query = self.session.query(ChannelORM)
        if active_only:
            query = query.filter(ChannelORM.active == True)
        return query.all()

    def get_channel(self, channel_id: str) -> Optional[ChannelORM]:
        """Get a channel by ID."""
        return self.session.query(ChannelORM).filter(ChannelORM.id == channel_id).first()

    def create_channel(self, channel: ChannelCreate) -> ChannelORM:
        """Create a new channel."""
        db_channel = ChannelORM(
            id=channel.id,
            name=channel.name,
            url=channel.url,
            domain=channel.domain,
            active=True,
        )
        self.session.add(db_channel)
        self.session.commit()
        self.session.refresh(db_channel)
        logger.info(f"Created channel: {channel.name} ({channel.id})")
        return db_channel

    def update_channel_checked(self, channel_id: str) -> None:
        """Update channel's last_checked_at timestamp."""
        channel = self.get_channel(channel_id)
        if channel:
            channel.last_checked_at = datetime.utcnow()
            self.session.commit()

    # Video operations
    def get_videos(
        self,
        status: Optional[str] = None,
        channel_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VideoORM]:
        """Get videos with optional filtering."""
        query = self.session.query(VideoORM)

        if status:
            query = query.filter(VideoORM.status == status)
        if channel_id:
            query = query.filter(VideoORM.channel_id == channel_id)

        query = query.order_by(desc(VideoORM.published_at))
        return query.offset(offset).limit(limit).all()

    def get_video(self, video_id: str) -> Optional[VideoORM]:
        """Get a video by ID."""
        return self.session.query(VideoORM).filter(VideoORM.id == video_id).first()

    def create_video(self, video_info: VideoInfo) -> VideoORM:
        """Create a new video."""
        db_video = VideoORM(
            id=video_info.id,
            channel_id=video_info.channel_id,
            title=video_info.title,
            url=video_info.url,
            published_at=video_info.published_at,
            duration_seconds=video_info.duration_seconds,
            status="pending",
        )
        self.session.add(db_video)
        self.session.commit()
        self.session.refresh(db_video)
        logger.debug(f"Created video: {video_info.title[:50]}...")
        return db_video

    def update_video_status(self, video_id: str, status: str) -> None:
        """Update a video's status."""
        video = self.get_video(video_id)
        if video:
            video.status = status
            self.session.commit()

    def get_pending_videos(self, limit: int = 10) -> list[VideoORM]:
        """Get pending videos for processing."""
        return self.get_videos(status="pending", limit=limit)

    def get_videos_since(self, since: datetime) -> list[VideoORM]:
        """Get videos published since a given datetime."""
        return (
            self.session.query(VideoORM)
            .filter(VideoORM.published_at >= since)
            .filter(VideoORM.status == "processed")
            .order_by(desc(VideoORM.published_at))
            .all()
        )

    # Transcript operations
    def get_transcript(self, video_id: str) -> Optional[TranscriptORM]:
        """Get transcript for a video."""
        return (
            self.session.query(TranscriptORM)
            .filter(TranscriptORM.video_id == video_id)
            .first()
        )

    def create_transcript(
        self,
        video_id: str,
        text: str,
        source: str,
        language: str = "en",
    ) -> TranscriptORM:
        """Create a transcript record."""
        db_transcript = TranscriptORM(
            video_id=video_id,
            text=text,
            source=source,
            language=language,
        )
        self.session.add(db_transcript)
        self.session.commit()
        self.session.refresh(db_transcript)
        logger.debug(f"Saved transcript for video: {video_id}")
        return db_transcript

    # Summary operations
    def get_summary(self, video_id: str) -> Optional[SummaryORM]:
        """Get the latest summary for a video."""
        return (
            self.session.query(SummaryORM)
            .filter(SummaryORM.video_id == video_id)
            .order_by(desc(SummaryORM.created_at))
            .first()
        )

    def create_summary(
        self,
        video_id: str,
        model: str,
        summary_text: str,
        key_points: list[str],
        category: str = "",
    ) -> SummaryORM:
        """Create a summary record."""
        db_summary = SummaryORM(
            video_id=video_id,
            model=model,
            summary_text=summary_text,
            key_points=json.dumps(key_points),
            category=category,
        )
        self.session.add(db_summary)
        self.session.commit()
        self.session.refresh(db_summary)
        logger.debug(f"Saved summary for video: {video_id}")
        return db_summary

    # Run operations
    def create_run(self) -> RunORM:
        """Create a new pipeline run."""
        db_run = RunORM(started_at=datetime.utcnow())
        self.session.add(db_run)
        self.session.commit()
        self.session.refresh(db_run)
        logger.info(f"Started pipeline run: {db_run.id}")
        return db_run

    def complete_run(
        self,
        run_id: int,
        new_videos: int = 0,
        processed: int = 0,
        errors: int = 0,
        status: str = "completed",
    ) -> None:
        """Complete a pipeline run."""
        run = self.session.query(RunORM).filter(RunORM.id == run_id).first()
        if run:
            run.finished_at = datetime.utcnow()
            run.new_videos = new_videos
            run.processed = processed
            run.errors = errors
            run.status = status
            run.runtime_seconds = (run.finished_at - run.started_at).total_seconds()
            self.session.commit()
            logger.info(
                f"Completed run {run_id}: {new_videos} new, {processed} processed, {errors} errors"
            )

    def get_runs(self, limit: int = 10) -> list[RunORM]:
        """Get recent pipeline runs."""
        return (
            self.session.query(RunORM)
            .order_by(desc(RunORM.started_at))
            .limit(limit)
            .all()
        )

    def get_latest_run(self) -> Optional[RunORM]:
        """Get the most recent pipeline run."""
        return self.session.query(RunORM).order_by(desc(RunORM.started_at)).first()

    # Statistics
    def get_stats(self) -> dict:
        """Get database statistics."""
        total_channels = self.session.query(func.count(ChannelORM.id)).scalar() or 0
        active_channels = (
            self.session.query(func.count(ChannelORM.id))
            .filter(ChannelORM.active == True)
            .scalar()
            or 0
        )
        total_videos = self.session.query(func.count(VideoORM.id)).scalar() or 0
        processed_videos = (
            self.session.query(func.count(VideoORM.id))
            .filter(VideoORM.status == "processed")
            .scalar()
            or 0
        )
        pending_videos = (
            self.session.query(func.count(VideoORM.id))
            .filter(VideoORM.status == "pending")
            .scalar()
            or 0
        )
        failed_videos = (
            self.session.query(func.count(VideoORM.id))
            .filter(VideoORM.status.in_(["failed", "no_transcript"]))
            .scalar()
            or 0
        )
        total_transcripts = (
            self.session.query(func.count(TranscriptORM.id)).scalar() or 0
        )
        total_summaries = self.session.query(func.count(SummaryORM.id)).scalar() or 0

        return {
            "total_channels": total_channels,
            "active_channels": active_channels,
            "total_videos": total_videos,
            "processed_videos": processed_videos,
            "pending_videos": pending_videos,
            "failed_videos": failed_videos,
            "total_transcripts": total_transcripts,
            "total_summaries": total_summaries,
        }
