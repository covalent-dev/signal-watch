#!/bin/bash
# Signal Watch scheduler wrapper script
# Add to crontab for automated polling:
# */15 * * * * /path/to/run_signal_watch.sh poll
# 0 6 * * * /path/to/run_signal_watch.sh digest

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Set Python path
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

case "${1:-poll}" in
    poll)
        echo "[$(date)] Starting poll..."
        python scripts/poll.py
        echo "[$(date)] Poll complete"
        ;;
    digest)
        echo "[$(date)] Generating digest..."
        python scripts/generate_digest.py
        echo "[$(date)] Digest complete"
        ;;
    server)
        echo "[$(date)] Starting server..."
        uvicorn src.main:app --host 0.0.0.0 --port 8000
        ;;
    *)
        echo "Usage: $0 {poll|digest|server}"
        exit 1
        ;;
esac
