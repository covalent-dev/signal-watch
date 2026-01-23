# Signal Watch

Always-fresh domain intelligence from YouTube, built as a production-grade data platform.

## Overview

Signal Watch is an automated system that watches domain-specific YouTube content (starting with AI channels), ingests video metadata + transcripts, summarizes using local LLMs, and serves insights via a REST API.

## Features

- **YouTube Channel Polling**: RSS-based polling for new videos from configured channels
- **Transcript Fetching**: Automatic transcript extraction using YouTube's caption system
- **LLM Summarization**: Local summarization using Ollama (deepseek-coder-v2:16b)
- **REST API**: FastAPI-powered endpoints for videos, transcripts, summaries, and digests
- **Daily Digests**: Automated daily digest generation in JSON and Markdown formats
- **Daily Brief Integration**: Output feed compatible with daily-brief-agent

## Quick Start

### Prerequisites

- Python 3.11+
- Ollama running locally with `deepseek-coder-v2:16b` model

### Installation

```bash
cd ~/covalent-dev/signal-watch

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
python -m pip install -r requirements.txt
```

Notes:
- The command is `python3 -m venv .venv` (space before `.venv`). If you run `python3 -m venv/.venv`, Python will treat `venv/.venv` as a module name and fail.
- If you use `pyenv`, set a local version first (e.g. `pyenv local 3.11.9`) so `python`/`pip` resolve correctly in this repo.

### Configuration

Edit `config/channels.yaml` to customize your channel watchlist:

```yaml
channels:
  - id: "UCbfYPyITQ-7l4upoX8nvctg"
    name: "Two Minute Papers"
    domain: "ai"
    priority: 1
```

### Running

```bash
# Start the API server
uvicorn src.main:app --reload

# Or use the wrapper script
./scripts/run_signal_watch.sh server
```

API will be available at `http://localhost:8000`

### Manual Operations

```bash
# Trigger a poll manually
./scripts/run_signal_watch.sh poll

# Generate daily digest
./scripts/run_signal_watch.sh digest
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/channels` | List all channels |
| POST | `/channels` | Add a channel |
| GET | `/videos` | List videos (paginated, filterable) |
| GET | `/videos/{id}` | Get video details + transcript + summary |
| GET | `/videos/{id}/transcript` | Get raw transcript |
| GET | `/digests/latest` | Get latest daily digest |
| GET | `/digests/{date}` | Get digest for specific date |
| POST | `/poll` | Trigger manual poll |
| GET | `/runs` | List recent pipeline runs |
| GET | `/stats` | Database statistics |

## Project Structure

```
signal-watch/
├── src/
│   ├── main.py              # FastAPI app + orchestrator
│   ├── config.py            # Config loading
│   ├── models.py            # Pydantic + SQLAlchemy models
│   ├── database.py          # SQLite connection
│   ├── sources/
│   │   └── youtube.py       # YouTube RSS polling
│   ├── processors/
│   │   ├── dedup.py         # Deduplication
│   │   ├── transcript.py    # Transcript fetching
│   │   └── summarize.py     # LLM summarization
│   ├── storage/
│   │   └── repository.py    # CRUD operations
│   └── api/
│       └── routes.py        # FastAPI endpoints
├── config/
│   └── channels.yaml        # Channel watchlist
├── prompts/
│   └── summarize.md         # LLM prompt template
├── data/
│   ├── transcripts/         # Raw transcript files
│   ├── videos/              # Per-video JSON
│   └── digests/             # Daily digests
├── scripts/
│   ├── poll.py              # Manual poll
│   ├── generate_digest.py   # Digest generation
│   └── run_signal_watch.sh  # Scheduler wrapper
└── tests/
```

## Scheduling

### Using cron

```bash
# Poll every 15 minutes
*/15 * * * * /path/to/signal-watch/scripts/run_signal_watch.sh poll >> /var/log/signal-watch.log 2>&1

# Generate digest at 6 AM
0 6 * * * /path/to/signal-watch/scripts/run_signal_watch.sh digest >> /var/log/signal-watch.log 2>&1
```

### Using launchd (macOS)

Create `~/Library/LaunchAgents/com.signal-watch.poll.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.signal-watch.poll</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/signal-watch/scripts/run_signal_watch.sh</string>
        <string>poll</string>
    </array>
    <key>StartInterval</key>
    <integer>900</integer>
</dict>
</plist>
```

Load with: `launchctl load ~/Library/LaunchAgents/com.signal-watch.poll.plist`

## Daily Brief Integration

Signal Watch outputs `signal_watch_feed.json` that Daily Brief Agent can consume:

```yaml
# In daily-brief-agent feeds.yaml
feeds:
  - name: "Signal Watch (YouTube AI)"
    url: "file:///path/to/signal-watch/data/digests/signal_watch_feed.json"
    type: "json"
    category: "AI/YouTube"
```

## Testing

```bash
pytest tests/ -v
```

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite (V1)
- **LLM**: Ollama (local)
- **Transcript API**: youtube-transcript-api
- **RSS Parsing**: feedparser

## Roadmap

- **V2**: PostgreSQL, Next.js frontend, Docker Compose
- **V3**: Grafana observability, GitHub Actions CI/CD
- **V4**: RAG with vector search, multi-agent orchestration

## License

MIT
