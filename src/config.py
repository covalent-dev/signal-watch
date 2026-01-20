"""Configuration loading for Signal Watch."""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChannelConfig(BaseModel):
    """Configuration for a YouTube channel to watch."""
    id: str
    name: str
    url: str = ""
    domain: str = "ai"
    priority: int = 10


class SettingsConfig(BaseModel):
    """Pipeline settings."""
    poll_interval_minutes: int = 15
    max_videos_per_poll: int = 10
    transcript_timeout_seconds: int = 30
    summary_model: str = "deepseek-coder-v2:16b"
    digest_hour: int = 6


class StorageConfig(BaseModel):
    """Storage paths."""
    database: str = "data/signal_watch.db"
    transcripts_dir: str = "data/transcripts"
    digests_dir: str = "data/digests"


class Config(BaseModel):
    """Full configuration."""
    channels: list[ChannelConfig] = []
    settings: SettingsConfig = SettingsConfig()
    storage: StorageConfig = StorageConfig()


class AppSettings(BaseSettings):
    """Application settings from environment."""
    model_config = SettingsConfigDict(env_prefix="SIGNAL_WATCH_")

    config_path: str = "config/channels.yaml"
    log_level: str = "INFO"
    ollama_host: str = "http://localhost:11434"


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = os.getenv("SIGNAL_WATCH_CONFIG_PATH", "config/channels.yaml")

    root = get_project_root()
    full_path = root / config_path

    if not full_path.exists():
        return Config()

    with open(full_path) as f:
        data = yaml.safe_load(f)

    return Config(**data)


def get_settings() -> AppSettings:
    """Get application settings."""
    return AppSettings()


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration."""
    global _config
    if _config is None:
        _config = load_config()
    return _config
