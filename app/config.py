"""
Container Security Falcon — Application Configuration

All sensitive values are loaded from environment variables.
NEVER hardcode secrets, tokens, or passwords in this file.
"""

import os


class BaseConfig:
    """Base configuration shared across all environments."""

    # Security: Always generate SECRET_KEY from environment
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

    # Application metadata
    APP_NAME = "Container Security Falcon"
    APP_VERSION = os.getenv("APP_VERSION", "0.1.0")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Metrics
    ENABLE_METRICS = True


class DevelopmentConfig(BaseConfig):
    """Development configuration with debug enabled."""

    DEBUG = True
    LOG_LEVEL = "DEBUG"


class TestingConfig(BaseConfig):
    """Testing configuration with testing flag enabled."""

    TESTING = True
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    ENABLE_METRICS = False  # Disable metrics during tests


class ProductionConfig(BaseConfig):
    """Production configuration with strict security settings."""

    DEBUG = False
    TESTING = False
    LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING")

    # In production, SECRET_KEY must be set via environment
    SECRET_KEY = os.environ.get("SECRET_KEY")

    @classmethod
    def init_app(cls, app):
        """Validate production configuration on startup."""
        if not cls.SECRET_KEY:
            raise ValueError(
                "SECRET_KEY environment variable must be set in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )


# Configuration registry
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
