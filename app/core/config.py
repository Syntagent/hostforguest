"""
Application configuration using Pydantic settings.

Infrastructure-only configuration for the Croatian tourist host platform.
User-specific settings (API keys, preferences) are stored in the database.
"""

from typing import List
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Infrastructure settings loaded from environment variables.

    Only contains server, database, and security settings.
    User-specific settings (API keys, preferences) are stored in the database.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application Configuration
    app_name: str = "TouristGuideLocal"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"

    # Server Configuration
    host: str = "localhost"
    port: int = 8000

    # PostgreSQL Configuration (Primary Database)
    postgres_server: str = "localhost"
    postgres_user: str = "tourist_guide_user"
    postgres_password: str = ""  # Empty password for trust authentication
    postgres_db: str = "tourist_guide_db"
    postgres_port: int = 5434  # Updated to match Docker port
    postgres_echo: bool = False

    # SQLite Database (Development Fallback)
    database_url: str = "sqlite+aiosqlite:///./tourist_guide.db"
    database_echo: bool = False

    # Database Selection
    use_postgresql: bool = True  # True for production/Docker, False for dev

    # Security Configuration
    secret_key: str = "your-super-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # API Configuration
    api_v1_str: str = "/api/v1"
    cors_origins: str = (
        "http://localhost:3000,http://localhost:3001,http://localhost:3002,"
        "http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002,"
        "http://localhost:8080"
    )

    # Croatian Tourism Defaults (can be overridden per host in database)
    default_location: str = "Lovran, Croatia"
    default_coordinates: str = "45.2919,14.2742"  # Changed to string to avoid parsing issues
    max_group_size: int = 12
    access_code_length: int = 8
    access_code_expire_hours: int = 168  # 7 days

    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    # Booking.com / channel connectivity (Connectivity API–style; base URL overridable)
    booking_com_api_base: str = "https://supply-xml.booking.com"
    booking_com_request_timeout_seconds: float = 60.0
    booking_com_max_retries: int = 3
    channel_webhook_secret: str = ""
    maintenance_webhook_secret: str = ""
    # Optional: POST /api/v1/maintenance/jobs/run-preventive-global with X-Maintenance-Job-Secret (cron / multi-instance)
    maintenance_job_secret: str = ""
    # Optional explicit Fernet key (44 chars base64). If empty, crypto_util derives from secret_key.
    channel_encryption_key: str = ""

    # Local dev: auto-create host for login page "Dev Login"
    dev_login_seed_enabled: bool = True
    # When True, seed runs even if ENVIRONMENT=production (e.g. Docker Compose local stack).
    dev_login_seed_force: bool = False
    dev_login_seed_email: str = "dev@touristguide.local"
    dev_login_seed_password: str = "devlogin123"

    @property
    def is_development(self) -> bool:
        return (self.environment or "").strip().lower() == "development"

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.is_development:
            return self

        default_secret = "your-super-secret-key-here-change-in-production"
        if not self.secret_key or self.secret_key == default_secret or len(self.secret_key) < 32:
            raise ValueError(
                "SECRET_KEY must be set to a strong value of at least 32 characters "
                "when ENVIRONMENT is not development."
            )

        if self.dev_login_seed_force:
            raise ValueError("DEV_LOGIN_SEED_FORCE must not be enabled outside development.")

        if self.use_postgresql and not self.postgres_password:
            raise ValueError("POSTGRES_PASSWORD must be set when ENVIRONMENT is not development.")

        return self

    @property
    def postgres_url(self) -> str:
        """
        Build PostgreSQL connection URL.

        Returns:
            PostgreSQL connection string
        """
        return f"postgresql://{self.postgres_user}@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"

    @property
    def async_postgres_url(self) -> str:
        """
        Build async PostgreSQL connection URL.

        Returns:
            Async PostgreSQL connection string
        """
        if self.postgres_password:
            return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"
        else:
            return f"postgresql+asyncpg://{self.postgres_user}@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"

    @property
    def cors_origins_list(self) -> List[str]:
        """
        Parse CORS origins from string to list.

        Returns:
            List of CORS origins
        """
        if not self.cors_origins:
            return ["http://localhost:3000", "http://localhost:8080"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# Global settings instance
settings = Settings()
