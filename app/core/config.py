from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "CRM Multi-Agent API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    # Coloca tu Gemini API key en el archivo .env como: GEMINI_API_KEY=tu_key_aqui
    GEMINI_API_KEY: Optional[str] = None
    # SLA threshold in hours: messages older than this are considered a breach
    SLA_THRESHOLD_HOURS: float = 2.0

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
