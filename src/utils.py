"""Shared utilities for Signal Watch."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from .config import get_project_root


def setup_logging(name: str = "signal_watch", level: str = "INFO") -> logging.Logger:
    """Set up logging with file and console handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler
    log_dir = get_project_root() / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(
        log_dir / f"signal_watch_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "signal_watch") -> logging.Logger:
    """Get or create a logger."""
    return setup_logging(name)


def save_json(data: dict, filepath: Path) -> None:
    """Save data as JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_json(filepath: Path) -> dict | None:
    """Load data from JSON file."""
    if not filepath.exists():
        return None
    with open(filepath) as f:
        return json.load(f)


def save_text(text: str, filepath: Path) -> None:
    """Save text to file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        f.write(text)


def load_text(filepath: Path) -> str | None:
    """Load text from file."""
    if not filepath.exists():
        return None
    with open(filepath) as f:
        return f.read()


def format_duration(seconds: int | None) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds is None:
        return "Unknown"

    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def youtube_video_url(video_id: str) -> str:
    """Generate YouTube video URL from ID."""
    return f"https://www.youtube.com/watch?v={video_id}"


def youtube_channel_url(channel_id: str) -> str:
    """Generate YouTube channel URL from ID."""
    return f"https://www.youtube.com/channel/{channel_id}"
