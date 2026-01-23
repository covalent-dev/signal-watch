#!/usr/bin/env python3
"""Generate daily digest script."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_db_session, init_db
from src.main import generate_daily_digest
from src.utils import get_logger

logger = get_logger("digest")


def main():
    """Generate the daily digest."""
    logger.info("Generating daily digest...")

    # Initialize database
    init_db()

    # Generate digest
    with get_db_session() as session:
        digest_path = generate_daily_digest(session)

    logger.info(f"Digest generated: {digest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
