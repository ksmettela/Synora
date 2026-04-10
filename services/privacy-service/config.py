"""Configuration management for Privacy Service."""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Service
    SERVICE_NAME: str = "privacy-service"
    DEBUG: bool = False
    VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://acraas:acraas@localhost:5432/acraas"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_POOL_SIZE: int = 20

    # AWS S3
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AUDIT_LOG_BUCKET: str = os.getenv("AUDIT_LOG_BUCKET", "acraas-audit-log")

    # Kafka (for consent events)
    KAFKA_BOOTSTRAP_SERVERS: list[str] = [
        os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    ]
    KAFKA_CONSENT_TOPIC: str = "consent.events"

    # Security
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", "your-super-secret-key-change-in-production"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_SECONDS: int = 3600

    # Privacy
    CCPA_DELETION_DEADLINE_HOURS: int = 24
    GDPR_DELETION_DEADLINE_HOURS: int = 72
    GDPR_DSAR_DEADLINE_HOURS: int = 72

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
