from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "CRM Multi-Agent API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    # Set this in a .env file for LLM-powered agents (not needed for mock mode)
    OPENAI_API_KEY: Optional[str] = None
    # SLA threshold in hours: messages older than this are considered a breach
    SLA_THRESHOLD_HOURS: float = 2.0

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
