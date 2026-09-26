import pytest

from api.runtime_config import load_runtime_config


def _clear(monkeypatch):
    for key in (
        "AVIA_ENV",
        "AVIA_DATABASE_URL",
        "AVIA_AUTH_MODE",
        "AVIA_CORS_ORIGINS",
        "AVIA_JWT_JWKS_URL",
        "AVIA_JWT_PUBLIC_KEY",
        "AVIA_JWT_SECRET",
        "AVIA_STORAGE_MODE",
        "AVIA_STORAGE_BUCKET",
    ):
        monkeypatch.delenv(key, raising=False)


def test_development_config_allows_local_defaults(monkeypatch):
    _clear(monkeypatch)
    config = load_runtime_config()

    assert config.environment == "development"
    assert config.auth_mode == "disabled"
    assert config.production is False
    assert config.cors_origins


def test_production_rejects_insecure_defaults(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("AVIA_ENV", "production")

    with pytest.raises(RuntimeError) as exc:
        load_runtime_config()

    message = str(exc.value)
    assert "AVIA_DATABASE_URL" in message
    assert "AVIA_AUTH_MODE" in message
    assert "AVIA_CORS_ORIGINS" in message


def test_production_accepts_managed_db_jwt_and_restricted_cors(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("AVIA_ENV", "production")
    monkeypatch.setenv(
        "AVIA_DATABASE_URL",
        "postgresql+psycopg://user:pass@example.com/db",
    )
    monkeypatch.setenv("AVIA_AUTH_MODE", "jwt")
    monkeypatch.setenv(
        "AVIA_CORS_ORIGINS",
        "https://app.example.com,https://admin.example.com",
    )
    monkeypatch.setenv("AVIA_STORAGE_MODE", "s3")
    monkeypatch.setenv("AVIA_STORAGE_BUCKET", "avia-production")
    monkeypatch.setenv(
        "AVIA_JWT_JWKS_URL",
        "https://auth.example.com/.well-known/jwks.json",
    )

    config = load_runtime_config()

    assert config.production is True
    assert config.auth_mode == "jwt"
    assert config.jwt_jwks_url
    assert "*" not in config.cors_origins


def test_production_rejects_wildcard_cors(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("AVIA_ENV", "production")
    monkeypatch.setenv(
        "AVIA_DATABASE_URL",
        "postgresql+psycopg://user:pass@example.com/db",
    )
    monkeypatch.setenv("AVIA_AUTH_MODE", "jwt")
    monkeypatch.setenv("AVIA_CORS_ORIGINS", "*")
    monkeypatch.setenv("AVIA_JWT_SECRET", "secret")
    monkeypatch.setenv("AVIA_STORAGE_MODE", "s3")
    monkeypatch.setenv("AVIA_STORAGE_BUCKET", "avia-production")

    with pytest.raises(RuntimeError) as exc:
        load_runtime_config()

    assert "Wildcard CORS" in str(exc.value)



def test_production_requires_cloud_artifact_storage(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("AVIA_ENV", "production")
    monkeypatch.setenv("AVIA_DATABASE_URL", "postgresql+psycopg://u:p@example.com/db")
    monkeypatch.setenv("AVIA_AUTH_MODE", "jwt")
    monkeypatch.setenv("AVIA_CORS_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("AVIA_JWT_SECRET", "secret")

    with pytest.raises(RuntimeError) as exc:
        load_runtime_config()

    message = str(exc.value)
    assert "AVIA_STORAGE_MODE" in message
    assert "AVIA_STORAGE_BUCKET" in message
