from __future__ import annotations

import os
from dataclasses import dataclass


def _csv(value: str | None) -> list[str]:
    return [
        item.strip()
        for item in str(value or "").split(",")
        if item.strip()
    ]


@dataclass(frozen=True)
class RuntimeConfig:
    environment: str
    database_url: str | None
    auth_mode: str
    cors_origins: tuple[str, ...]
    jwt_jwks_url: str | None
    jwt_has_static_key: bool
    storage_mode: str
    storage_bucket: str | None

    @property
    def production(self) -> bool:
        return self.environment == "production"

    def validate(self) -> None:
        errors: list[str] = []

        if self.production:
            if not self.database_url:
                errors.append("AVIA_DATABASE_URL is required in production.")
            if self.auth_mode != "jwt":
                errors.append("AVIA_AUTH_MODE must be 'jwt' in production.")
            if not self.cors_origins:
                errors.append("AVIA_CORS_ORIGINS is required in production.")
            if "*" in self.cors_origins:
                errors.append("Wildcard CORS is not allowed in production.")
            if self.storage_mode != "s3":
                errors.append("AVIA_STORAGE_MODE must be s3 in production.")
            if not self.storage_bucket:
                errors.append("AVIA_STORAGE_BUCKET is required in production.")
            if not (self.jwt_jwks_url or self.jwt_has_static_key):
                errors.append(
                    "Configure AVIA_JWT_JWKS_URL or a JWT verification key in production."
                )

        if errors:
            raise RuntimeError("Production configuration invalid: " + " ".join(errors))


def load_runtime_config() -> RuntimeConfig:
    environment = os.getenv("AVIA_ENV", "development").strip().lower()
    auth_mode = os.getenv("AVIA_AUTH_MODE", "disabled").strip().lower()
    database_url = os.getenv("AVIA_DATABASE_URL", "").strip() or None
    jwt_jwks_url = os.getenv("AVIA_JWT_JWKS_URL", "").strip() or None
    jwt_has_static_key = bool(
        os.getenv("AVIA_JWT_PUBLIC_KEY", "").strip()
        or os.getenv("AVIA_JWT_SECRET", "").strip()
    )

    default_cors = (
        "http://localhost:8081,http://localhost:19006"
        if environment != "production"
        else ""
    )
    cors_origins = tuple(
        _csv(os.getenv("AVIA_CORS_ORIGINS", default_cors))
    )

    storage_mode = os.getenv("AVIA_STORAGE_MODE", "local").strip().lower()
    storage_bucket = os.getenv("AVIA_STORAGE_BUCKET", "").strip() or None

    config = RuntimeConfig(
        environment=environment,
        database_url=database_url,
        auth_mode=auth_mode,
        cors_origins=cors_origins,
        jwt_jwks_url=jwt_jwks_url,
        jwt_has_static_key=jwt_has_static_key,
        storage_mode=storage_mode,
        storage_bucket=storage_bucket,
    )
    config.validate()
    return config
