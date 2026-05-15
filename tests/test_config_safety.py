import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_default_secret_key():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(
            environment="production",
            postgres_password="safe-db-password",
            secret_key="your-super-secret-key-here-change-in-production",
        )


def test_production_rejects_empty_postgres_password():
    with pytest.raises(ValidationError, match="POSTGRES_PASSWORD"):
        Settings(
            environment="production",
            secret_key="x" * 40,
            use_postgresql=True,
            postgres_password="",
        )


def test_production_rejects_forced_dev_login_seed():
    with pytest.raises(ValidationError, match="DEV_LOGIN_SEED_FORCE"):
        Settings(
            environment="production",
            secret_key="x" * 40,
            postgres_password="safe-db-password",
            dev_login_seed_force=True,
        )


def test_development_allows_local_defaults():
    settings = Settings(environment="development")

    assert settings.is_development is True
    assert settings.secret_key
