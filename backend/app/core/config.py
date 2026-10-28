"""
Application configuration loaded from environment variables.
Implements NFR-01 (no hardcoded credentials) and COM-01 (documented assumptions).
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings  # fallback: use plain pydantic


class Settings:
    """Application settings loaded from environment variables with safe defaults for development."""

    # Application
    APP_NAME: str = os.getenv("APP_NAME", "Academic Course Scheduling Decision-Support System")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./acs_dev.db"
    )

    # JWT Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_use_a_long_random_string")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # CORS
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")

    # File upload limits (NFR upload safety)
    MAX_UPLOAD_SIZE_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(50 * 1024 * 1024)))  # 50 MB
    ALLOWED_UPLOAD_EXTENSIONS: set = {"csv"}

    # Analytics thresholds (prototype assumptions, configurable, not CSUSB policies)
    HIGH_UTILIZATION_THRESHOLD: float = float(os.getenv("HIGH_UTILIZATION_THRESHOLD", "85.0"))
    LOW_UTILIZATION_THRESHOLD: float = float(os.getenv("LOW_UTILIZATION_THRESHOLD", "50.0"))
    FREQUENTLY_FULL_THRESHOLD: float = float(os.getenv("FREQUENTLY_FULL_THRESHOLD", "0.50"))
    INCREASING_DEMAND_SLOPE: float = float(os.getenv("INCREASING_DEMAND_SLOPE", "2.0"))
    MIN_TERMS_FOR_TREND: int = int(os.getenv("MIN_TERMS_FOR_TREND", "2"))
    FULL_CAPACITY_THRESHOLD: float = float(os.getenv("FULL_CAPACITY_THRESHOLD", "0.95"))

    # Method version for traceability (DR-03)
    ANALYTICS_METHOD_VERSION: str = os.getenv("ANALYTICS_METHOD_VERSION", "1.0.0")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
