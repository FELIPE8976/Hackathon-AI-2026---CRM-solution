from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "CRM Multi-Agent API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Empty string = "not set". Validators below reject blank values so a
    # missing env var is caught at startup with a clear error message.
    GEMINI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    GITHUB_TOKEN: str = ""
    DATABASE_URL: str = ""

    # Optional with a safe default
    SLA_THRESHOLD_HOURS: float = 2.0
    LOG_LEVEL: str = "INFO"

    # Comma-separated string of allowed CORS origins.
    # In .env: ALLOWED_ORIGINS=https://crm.miempresa.com,http://localhost:8501
    # Kept as str to avoid pydantic-settings attempting JSON parsing on list fields.
    ALLOWED_ORIGINS: str = ""

    # ── Auth ────────────────────────────────────────────────────────────────
    # JWT — used by the supervisor frontend
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # Supervisor credentials (single account, no DB required)
    # Generate password hash with: python -c "import bcrypt; print(bcrypt.hashpw('yourpassword'.encode(), bcrypt.gensalt()).decode())"
    SUPERVISOR_USERNAME: str = ""
    SUPERVISOR_PASSWORD_HASH: str = ""

    # API Key — used by the CRM bot (machine-to-machine)
    # Include in requests as:  X-Api-Key: <value>
    WEBHOOK_API_KEY: str = ""

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def allowed_origins_must_not_be_empty(cls, v: str) -> str:
        origins = [o.strip() for o in v.split(",") if o.strip()]
        if not origins:
            raise ValueError(
                "ALLOWED_ORIGINS is required. "
                "Set it in .env as a comma-separated list: "
                "ALLOWED_ORIGINS=https://crm.miempresa.com,http://localhost:8501"
            )
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @field_validator("GITHUB_TOKEN")
    @classmethod
    def github_token_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("GITHUB_TOKEN must not be empty")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def database_url_must_be_asyncpg(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("DATABASE_URL is required")
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use the 'postgresql+asyncpg://' scheme. "
                f"Got: '{v}'"
            )
        return v

    @field_validator("JWT_SECRET_KEY", "SUPERVISOR_USERNAME", "SUPERVISOR_PASSWORD_HASH", "WEBHOOK_API_KEY")
    @classmethod
    def auth_fields_must_not_be_empty(cls, v: str, info) -> str:
        if not v.strip():
            raise ValueError(f"{info.field_name} is required and must not be empty")
        return v

    @field_validator("SLA_THRESHOLD_HOURS")
    @classmethod
    def sla_threshold_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(
                f"SLA_THRESHOLD_HOURS must be greater than 0. Got: {v}"
            )
        return v


settings = Settings()
