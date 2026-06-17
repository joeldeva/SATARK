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

    DATABASE_URL: str = "postgresql+psycopg://satark:satark@127.0.0.1:5432/satark"

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

    LLM_PROVIDER: str = "ollama"  # ollama | openrouter | none
    LLM_MODEL: str = "gemma2:2b"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    LLM_REQUIRED: bool = True
    LLM_TIMEOUT_SECONDS: int = 45
    TRANSLATION_PROVIDER: str = "ollama"  # ollama | indictrans2 | bhashini | none
    TRANSLATION_MODEL: str = "gemma2:2b"
    TRANSLATION_TIMEOUT_SECONDS: int = 60
    INDIC_TRANS2_MODEL_PATH: Optional[str] = None

    # OpenRouter (online, OpenAI-compatible) — used when LLM_PROVIDER=openrouter.
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "nex-agi/nex-n2-pro:free"
    VECTOR_STORE: str = "auto"  # auto | chroma | postgres | local
    CHROMA_URL: str = "http://127.0.0.1:8002"
    CHROMA_DIR: str = str(PROJECT_ROOT / "data" / "chroma")

    REDIS_URL: str = "redis://localhost:6379/0"
    WHATSAPP_PROVIDER: str = "baileys"  # baileys | meta
    WHATSAPP_VERIFY_TOKEN: Optional[str] = None
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_API_VERSION: str = "v20.0"
    SUPERPLANE_WEBHOOK_URL: Optional[str] = None
    SUPERPLANE_TOKEN: Optional[str] = None
    TRUST_WEIGHT_VALIDATION: float = 0.40
    TRUST_WEIGHT_FRAUD: float = 0.30
    TRUST_WEIGHT_EVIDENCE: float = 0.15
    TRUST_WEIGHT_BEHAVIOUR: float = 0.15
    CONF_THRESHOLD: int = 70

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

    @property
    def trust_weights(self) -> dict[str, float]:
        return {
            "validation": self.TRUST_WEIGHT_VALIDATION,
            "fraud": self.TRUST_WEIGHT_FRAUD,
            "evidence": self.TRUST_WEIGHT_EVIDENCE,
            "behaviour": self.TRUST_WEIGHT_BEHAVIOUR,
        }

    @property
    def gemma_model(self) -> str:
        return self.LLM_MODEL


settings = Settings()
