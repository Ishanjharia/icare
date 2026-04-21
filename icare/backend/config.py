"""Application settings (environment variables)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """I-CARE backend configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Groq AI
    GROQ_API_KEY: str
    GROQ_MEDICAL_MODEL: str = "llama-3.1-70b-versatile"
    GROQ_FAST_MODEL: str = "llama-3.2-3b-preview"
    GROQ_WHISPER_MODEL: str = "whisper-large-v3-turbo"

    # Supabase PostgreSQL
    DATABASE_URL: str  # postgresql+asyncpg://...

    # InfluxDB Cloud
    INFLUXDB_URL: str
    INFLUXDB_TOKEN: str
    INFLUXDB_ORG: str = "icare"
    INFLUXDB_BUCKET: str = "vitals"

    # Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # SMS
    FAST2SMS_API_KEY: str

    # App
    FRONTEND_URL: str = "http://localhost:3000"
    ENVIRONMENT: str = "development"


settings = Settings()
