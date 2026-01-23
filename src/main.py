"""FastAPI application and pipeline orchestrator."""

import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy.orm import Session

from . import __version__
from .api import router
from .config import get_config, get_project_root, ChannelConfig
from .database import get_db_session, init_db
from .models import ChannelCreate, PollResponse
from .processors import Deduplicator, Summarizer, TranscriptFetcher
from .sources import YouTubeSource
from .storage import Repository
from .utils import get_logger, save_json, save_text

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting Signal Watch v{__version__}")

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Load channels from config
    load_channels_from_config()

    yield

    logger.info("Shutting down Signal Watch")


def load_channels_from_config():
    """Load channels from config file into database."""
    config = get_config()

    with get_db_session() as session:
        repo = Repository(session)

        for channel_config in config.channels:
            existing = repo.get_channel(channel_config.id)
            if not existing:
                channel = ChannelCreate(
                    id=channel_config.id,
                    name=channel_config.name,
                    url=channel_config.url,
                    domain=channel_config.domain,
                )
                repo.create_channel(channel)
                logger.info(f"Added channel from config: {channel_config.name}")


def run_pipeline(session: Session) -> PollResponse:
    """
    Run the full pipeline: poll -> fetch transcripts -> summarize.

    Args:
        session: Database session

    Returns:
        PollResponse with run statistics
    """
    config = get_config()
    repo = Repository(session)

    # Create run record
    run = repo.create_run()

    new_videos_count = 0
    processed_count = 0
    errors_count = 0

    try:
        # Phase 1: Poll channels for new videos
        logger.info("Starting poll phase...")
        new_videos_count = poll_channels(session)

        # Phase 2: Process pending videos (transcript + summary)
        logger.info("Starting processing phase...")
        processed_count, errors_count = process_pending_videos(session)

        # Complete run
        repo.complete_run(
            run_id=run.id,
            new_videos=new_videos_count,
            processed=processed_count,
            errors=errors_count,
            status="completed",
        )

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        repo.complete_run(
            run_id=run.id,
            new_videos=new_videos_count,
            processed=processed_count,
            errors=errors_count + 1,
            status="failed",
        )
        raise

    return PollResponse(
        status="completed",
        new_videos=new_videos_count,
        processed=processed_count,
        errors=errors_count,
        run_id=run.id,
    )


def poll_channels(session: Session) -> int:
    """
    Poll all active channels for new videos.

    Returns:
        Number of new videos discovered
    """
    config = get_config()
    repo = Repository(session)
    dedup = Deduplicator(session)

    channels = repo.get_channels(active_only=True)
    new_videos_total = 0

    with YouTubeSource(timeout=config.settings.transcript_timeout_seconds) as youtube:
        for channel in channels:
            try:
                logger.info(f"Polling channel: {channel.name}")

                videos = youtube.poll_channel(
                    channel.id,
                    max_videos=config.settings.max_videos_per_poll,
                )

                # Filter out duplicates
                video_ids = [v.id for v in videos]
                new_ids = dedup.filter_new_videos(video_ids)
                new_videos = [v for v in videos if v.id in new_ids]

                # Insert new videos
                for video_info in new_videos:
                    repo.create_video(video_info)
                    new_videos_total += 1

                # Update channel checked timestamp
                repo.update_channel_checked(channel.id)

                if new_videos:
                    logger.info(f"Found {len(new_videos)} new videos for {channel.name}")

            except Exception as e:
                logger.error(f"Failed to poll channel {channel.name}: {e}")

    logger.info(f"Poll complete: {new_videos_total} new videos")
    return new_videos_total


def process_pending_videos(session: Session) -> tuple[int, int]:
    """
    Process pending videos: fetch transcripts and generate summaries.

    Returns:
        Tuple of (processed_count, errors_count)
    """
    config = get_config()
    repo = Repository(session)

    transcript_fetcher = TranscriptFetcher()
    summarizer = Summarizer(model=config.settings.summary_model)

    pending = repo.get_pending_videos(limit=20)
    processed = 0
    errors = 0

    for video in pending:
        try:
            logger.info(f"Processing video: {video.title[:50]}...")

            # Fetch transcript
            result = transcript_fetcher.fetch(video.id)

            if not result.success:
                logger.warning(f"No transcript for {video.id}: {result.error}")
                repo.update_video_status(video.id, "no_transcript")
                errors += 1
                continue

            # Save transcript to database
            repo.create_transcript(
                video_id=video.id,
                text=result.text,
                source=result.source,
                language=result.language,
            )

            # Generate summary
            channel_name = video.channel.name if video.channel else "Unknown"
            summary_result = summarizer.summarize(
                video_id=video.id,
                title=video.title,
                channel=channel_name,
                transcript=result.text,
            )

            if summary_result.success:
                repo.create_summary(
                    video_id=video.id,
                    model=summary_result.model,
                    summary_text=summary_result.summary,
                    key_points=summary_result.key_points,
                    category=summary_result.category,
                )
                repo.update_video_status(video.id, "processed")
                processed += 1
            else:
                logger.warning(f"Summary failed for {video.id}: {summary_result.error}")
                repo.update_video_status(video.id, "failed")
                errors += 1

        except Exception as e:
            logger.error(f"Failed to process video {video.id}: {e}")
            repo.update_video_status(video.id, "failed")
            errors += 1

    logger.info(f"Processing complete: {processed} processed, {errors} errors")
    return processed, errors


def generate_daily_digest(session: Session) -> Path:
    """
    Generate daily digest for videos from the last 24 hours.

    Returns:
        Path to the generated digest file
    """
    config = get_config()
    repo = Repository(session)

    since = datetime.utcnow() - timedelta(hours=24)
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

            digest_videos.append({
                "title": video.title,
                "link": video.url,
                "channel": video.channel.name if video.channel else "Unknown",
                "published": video.published_at.isoformat() if video.published_at else None,
                "summary": summary.summary_text,
                "key_points": key_points,
                "category": summary.category or "ai",
            })

    # Sort by channel priority (using published_at as proxy for now)
    digest_videos.sort(key=lambda x: x.get("published", ""), reverse=True)

    today = datetime.utcnow().date().isoformat()

    # Save JSON digest
    digest_data = {
        "source": "signal-watch",
        "generated_at": datetime.utcnow().isoformat(),
        "date": today,
        "videos": digest_videos,
    }

    digests_dir = get_project_root() / config.storage.digests_dir
    json_path = digests_dir / f"digest_{today}.json"
    save_json(digest_data, json_path)

    # Save markdown digest
    md_content = generate_digest_markdown(digest_data)
    md_path = digests_dir / f"digest_{today}.md"
    save_text(md_content, md_path)

    # Also save as signal_watch_feed.json for Daily Brief integration
    feed_path = digests_dir / "signal_watch_feed.json"
    save_json(digest_data, feed_path)

    logger.info(f"Generated daily digest: {json_path}")
    return json_path


def generate_digest_markdown(digest_data: dict) -> str:
    """Generate markdown formatted digest."""
    lines = [
        f"# Signal Watch Daily Digest",
        f"**Date:** {digest_data['date']}",
        f"**Generated:** {digest_data['generated_at']}",
        "",
        "---",
        "",
    ]

    if not digest_data["videos"]:
        lines.append("*No new videos in the last 24 hours.*")
        return "\n".join(lines)

    for video in digest_data["videos"]:
        lines.append(f"## {video['title']}")
        lines.append(f"**Channel:** {video['channel']} | **Category:** {video['category']}")
        lines.append(f"**Link:** {video['link']}")
        lines.append("")
        lines.append(video["summary"])
        lines.append("")

        if video.get("key_points"):
            lines.append("**Key Points:**")
            for point in video["key_points"]:
                lines.append(f"- {point}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


# FastAPI app
app = FastAPI(
    title="Signal Watch",
    description="YouTube domain intelligence platform",
    version=__version__,
    lifespan=lifespan,
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
