from pathlib import Path
from typing import ClassVar, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=True)

    PROJECT_ROOT: ClassVar[Path] = Path(__file__).resolve().parents[3]

    APP_NAME: str = "SATARK - Survey Intelligence Platform"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = f"sqlite:///{(PROJECT_ROOT / 'data' / 'satark.db').as_posix()}"

    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    KNOWLEDGE_BASE_PATH: str = str(PROJECT_ROOT / "data")
    CORS_ORIGINS: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:3001,"
        "http://127.0.0.1:3001"
    )

    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "llama3.2:3b"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    LLM_REQUIRED: bool = True
    LLM_TIMEOUT_SECONDS: int = 45

    REDIS_URL: str = "redis://localhost:6379/0"

    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    BHASHINI_API_KEY: Optional[str] = None

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return True
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on", "debug", "dev", "development"}:
            return True
        if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
            return False
        return True

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def sqlite_path(self) -> Optional[Path]:
        if not self.DATABASE_URL.startswith("sqlite:///"):
            return None
        return Path(self.DATABASE_URL.replace("sqlite:///", "", 1))


settings = Settings()
