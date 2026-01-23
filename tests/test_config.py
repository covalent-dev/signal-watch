"""Tests for configuration loading."""

import pytest
from pathlib import Path

from src.config import Config, ChannelConfig, SettingsConfig, load_config, get_project_root


def test_channel_config_defaults():
    """Test ChannelConfig default values."""
    channel = ChannelConfig(id="test123", name="Test Channel")
    assert channel.domain == "ai"
    assert channel.priority == 10
    assert channel.url == ""


def test_settings_config_defaults():
    """Test SettingsConfig default values."""
    settings = SettingsConfig()
    assert settings.poll_interval_minutes == 15
    assert settings.max_videos_per_poll == 10
    assert settings.transcript_timeout_seconds == 30
    assert settings.digest_hour == 6


def test_config_defaults():
    """Test Config default values."""
    config = Config()
    assert config.channels == []
    assert isinstance(config.settings, SettingsConfig)


def test_get_project_root():
    """Test project root detection."""
    root = get_project_root()
    assert root.exists()
    assert (root / "src").exists() or root.name == "signal-watch"


def test_load_config_from_file():
    """Test loading config from YAML file."""
    config = load_config()
    # Should have channels from default config
    assert isinstance(config.channels, list)
