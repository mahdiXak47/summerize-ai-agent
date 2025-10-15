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


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Return cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
