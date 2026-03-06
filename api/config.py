"""Application configuration via pydantic-settings.

Loads settings from environment variables with sensible defaults for development.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Bridge Model API"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./bridge.db"

    # Auth
    admin_api_key: str = "bridge-admin-dev"

    # Model inference
    inference_provider: str = "ollama"  # ollama, vllm, huggingface
    model_name: str = "bridge-cli"
    ollama_base_url: str = "http://2070.zero:11434"
    vllm_base_url: str = "http://localhost:8001"
    hf_api_token: str = ""
    hf_inference_url: str = ""

    # Rate limiting
    rate_limit_per_minute: int = 60

    model_config = {"env_prefix": "BRIDGE_"}


settings = Settings()
