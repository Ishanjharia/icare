"""Application settings (environment variables)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """I-CARE backend configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Groq AI (optional at boot; required when calling AI routes)
    GROQ_API_KEY: str = ""
    GROQ_MEDICAL_MODEL: str = "llama-3.1-70b-versatile"
    GROQ_FAST_MODEL: str = "llama-3.2-3b-preview"
    GROQ_WHISPER_MODEL: str = "whisper-large-v3-turbo"

    # Supabase PostgreSQL (async). Read from env ``DATABASE_URL`` (case-insensitive on typical installs).
    # Default empty so the process can boot for ``/health`` even if the var is missing on Render; DB routes return 503 until set.
    DATABASE_URL: str = Field(
        default="",
        description="postgresql+asyncpg://user:password@host:port/db — URL-encode special chars in password (@ %40, [ %5B, ] %5D).",
    )

    # InfluxDB Cloud (optional; vitals history falls back when unset)
    INFLUXDB_URL: str = ""
    INFLUXDB_TOKEN: str = ""
    INFLUXDB_ORG: str = "icare"
    INFLUXDB_BUCKET: str = "vitals"

    # Auth (override SECRET_KEY in production)
    SECRET_KEY: str = Field(
        default="dev-only-change-me-32-characters-min!!",
        min_length=16,
        description="JWT signing secret; must be set to a strong value in production.",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # SMS (optional; log-only mode when unset)
    FAST2SMS_API_KEY: str = ""

    # App — comma-separated origins allowed (e.g. https://app.vercel.app,https://www.example.com)
    FRONTEND_URL: str = "http://localhost:5173,http://localhost:3000"
    # Extra CORS regex for Vercel preview URLs (set to empty to disable)
    CORS_ORIGIN_REGEX: str = r"https://.*\.vercel\.app"
    ENVIRONMENT: str = "development"


settings = Settings()
