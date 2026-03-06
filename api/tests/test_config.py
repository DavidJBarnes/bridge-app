"""Tests for application configuration."""

from api.config import Settings


def test_default_settings():
    """Default settings are loaded correctly."""
    s = Settings()
    assert s.app_name == "Bridge Model API"
    assert s.debug is False
    assert s.inference_provider == "ollama"
    assert s.rate_limit_per_minute == 60


def test_settings_env_prefix():
    """Settings use BRIDGE_ prefix for environment variables."""
    assert Settings.model_config["env_prefix"] == "BRIDGE_"
