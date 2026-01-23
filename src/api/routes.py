"""FastAPI route definitions."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_config, get_project_root
from ..database import get_db
from ..models import (
    ChannelCreate,
    ChannelResponse,
    DigestResponse,
    DigestVideo,
    HealthResponse,
    PollResponse,
    RunResponse,
    StatsResponse,
    TranscriptResponse,
    VideoDetailResponse,
    VideoResponse,
)
from ..processors import Summarizer
from ..storage import Repository
from .. import __version__

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    # Check database
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # Check Ollama
    summarizer = Summarizer()
    ollama_status = "ok" if summarizer.check_ollama_available() else "unavailable"

    return HealthResponse(
        status="healthy" if db_status == "ok" else "degraded",
        version=__version__,
        database=db_status,
        ollama=ollama_status,
    )


@router.get("/channels", response_model=list[ChannelResponse])
def list_channels(
    active_only: bool = Query(False, description="Only return active channels"),
    db: Session = Depends(get_db),
):
    """List all channels."""
    repo = Repository(db)
    channels = repo.get_channels(active_only=active_only)
    return channels


@router.post("/channels", response_model=ChannelResponse, status_code=201)
def create_channel(channel: ChannelCreate, db: Session = Depends(get_db)):
    """Add a new channel to watch."""
    repo = Repository(db)

    # Check if channel already exists
    existing = repo.get_channel(channel.id)
    if existing:
        raise HTTPException(status_code=400, detail="Channel already exists")

    return repo.create_channel(channel)


@router.get("/videos", response_model=list[VideoResponse])
def list_videos(
    status: Optional[str] = Query(None, description="Filter by status"),
    channel_id: Optional[str] = Query(None, description="Filter by channel"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """List videos with optional filtering."""
    repo = Repository(db)
    videos = repo.get_videos(status=status, channel_id=channel_id, limit=limit, offset=offset)

    # Add channel names
    result = []
    for video in videos:
        response = VideoResponse.model_validate(video)
        if video.channel:
            response.channel_name = video.channel.name
        result.append(response)

    return result


@router.get("/videos/{video_id}", response_model=VideoDetailResponse)
def get_video(video_id: str, db: Session = Depends(get_db)):
    """Get video details including transcript and summary."""
    repo = Repository(db)
    video = repo.get_video(video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    response = VideoDetailResponse(
        id=video.id,
        channel_id=video.channel_id,
        title=video.title,
        url=video.url,
        published_at=video.published_at,
        duration_seconds=video.duration_seconds,
        status=video.status,
        created_at=video.created_at,
    )

    if video.channel:
        response.channel_name = video.channel.name

    if video.transcript:
        response.transcript = video.transcript.text

    summary = repo.get_summary(video_id)
    if summary:
        response.summary = summary.summary_text
        response.category = summary.category
        if summary.key_points:
            try:
                response.key_points = json.loads(summary.key_points)
            except json.JSONDecodeError:
                response.key_points = []

    return response


@router.get("/videos/{video_id}/transcript", response_model=TranscriptResponse)
def get_video_transcript(video_id: str, db: Session = Depends(get_db)):
    """Get raw transcript for a video."""
    repo = Repository(db)
    transcript = repo.get_transcript(video_id)

    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    return transcript


@router.get("/digests/latest", response_model=DigestResponse)
def get_latest_digest(db: Session = Depends(get_db)):
    """Get the latest daily digest."""
    config = get_config()
    digests_dir = get_project_root() / config.storage.digests_dir

    # Find the most recent digest JSON file
    digest_files = sorted(digests_dir.glob("digest_*.json"), reverse=True)

    if not digest_files:
        # Generate on-the-fly if no saved digest
        return generate_digest_for_date(datetime.utcnow().date().isoformat(), db)

    # Load the most recent digest
    with open(digest_files[0]) as f:
        data = json.load(f)

    return DigestResponse(**data)


@router.get("/digests/{date}", response_model=DigestResponse)
def get_digest_by_date(date: str, db: Session = Depends(get_db)):
    """Get digest for a specific date (YYYY-MM-DD)."""
    config = get_config()
    digests_dir = get_project_root() / config.storage.digests_dir
    digest_path = digests_dir / f"digest_{date}.json"

    if digest_path.exists():
        with open(digest_path) as f:
            data = json.load(f)
        return DigestResponse(**data)

    # Generate on-the-fly
    return generate_digest_for_date(date, db)


def generate_digest_for_date(date: str, db: Session) -> DigestResponse:
    """Generate a digest for a specific date."""
    try:
        target_date = datetime.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    repo = Repository(db)

    # Get videos from the last 24 hours of the target date
    since = target_date - timedelta(days=1)
    videos = repo.get_videos_since(since)

    digest_videos = []
    for video in videos:
        summary = repo.get_summary(video.id)
        if summary:
            key_points = []
            if summary.key_points:
                try:
                    key_points = json.loads(summary.key_points)
                except json.JSONDecodeError:
                    pass

            digest_videos.append(
                DigestVideo(
                    title=video.title,
                    link=video.url,
                    channel=video.channel.name if video.channel else "Unknown",
                    published=video.published_at,
                    summary=summary.summary_text,
                    key_points=key_points,
                    category=summary.category or "ai",
                )
            )

    return DigestResponse(
        source="signal-watch",
        generated_at=datetime.utcnow(),
        date=date,
        videos=digest_videos,
    )


@router.post("/poll", response_model=PollResponse)
def trigger_poll(db: Session = Depends(get_db)):
    """Trigger a manual poll of all channels."""
    # Import here to avoid circular imports
    from ..main import run_pipeline

    result = run_pipeline(db)
    return result


@router.get("/runs", response_model=list[RunResponse])
def list_runs(
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    db: Session = Depends(get_db),
):
    """List recent pipeline runs."""
    repo = Repository(db)
    return repo.get_runs(limit=limit)


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """Get database statistics."""
    repo = Repository(db)
    stats = repo.get_stats()

    latest_run = repo.get_latest_run()
    run_response = None
    if latest_run:
        run_response = RunResponse.model_validate(latest_run)

    return StatsResponse(
        total_channels=stats["total_channels"],
        active_channels=stats["active_channels"],
        total_videos=stats["total_videos"],
        processed_videos=stats["processed_videos"],
        pending_videos=stats["pending_videos"],
        failed_videos=stats["failed_videos"],
        total_transcripts=stats["total_transcripts"],
        total_summaries=stats["total_summaries"],
        last_run=run_response,
    )
