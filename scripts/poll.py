#!/usr/bin/env python3
"""Manual poll trigger script."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_db_session, init_db
from src.main import run_pipeline
from src.utils import get_logger

logger = get_logger("poll")


def main():
    """Run a manual poll."""
    logger.info("Starting manual poll...")

    # Initialize database
    init_db()

    # Run the pipeline
    with get_db_session() as session:
        result = run_pipeline(session)

    logger.info(
        f"Poll complete: {result.new_videos} new videos, "
        f"{result.processed} processed, {result.errors} errors"
    )

    return 0 if result.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
