import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    """Runtime settings loaded from environment variables."""
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    openai_model: str = os.environ.get("OPENAI_MODEL", "gpt-4.1")
    request_timeout_seconds: float = float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "15"))
    health_deep_timeout_seconds: float = float(os.environ.get("HEALTH_DEEP_TIMEOUT_SECONDS", "1"))
    # LLM provider selection: "openai" or "openrouter".
    llm_provider: str = os.environ.get("LLM_PROVIDER", "openai")
    # OpenRouter configuration.
    openrouter_api_key: str = os.environ.get("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.environ.get("OPENROUTER_MODEL", "tngtech/deepseek-r1t2-chimera:free")
    openrouter_site_url: str = os.environ.get("OPENROUTER_SITE_URL", "")
    openrouter_site_name: str = os.environ.get("OPENROUTER_SITE_NAME", "")


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Return cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
