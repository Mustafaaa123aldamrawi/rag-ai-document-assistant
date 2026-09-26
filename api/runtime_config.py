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
    account_delete_provider: str
    supabase_url: str | None
    supabase_service_role_key: str | None
    support_email: str | None
    public_base_url: str | None

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
            if self.account_delete_provider == "disabled":
                errors.append(
                    "AVIA_ACCOUNT_DELETE_PROVIDER must be configured in production."
                )
            if self.account_delete_provider == "supabase":
                if not self.supabase_url:
                    errors.append("AVIA_SUPABASE_URL is required in production.")
                if not self.supabase_service_role_key:
                    errors.append(
                        "AVIA_SUPABASE_SERVICE_ROLE_KEY is required in production."
                    )
            if not self.support_email:
                errors.append("AVIA_SUPPORT_EMAIL is required in production.")
            if not self.public_base_url:
                errors.append("AVIA_PUBLIC_BASE_URL is required in production.")
            elif not self.public_base_url.startswith("https://"):
                errors.append("AVIA_PUBLIC_BASE_URL must use HTTPS in production.")
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
    account_delete_provider = os.getenv(
        "AVIA_ACCOUNT_DELETE_PROVIDER", "disabled"
    ).strip().lower()
    supabase_url = os.getenv("AVIA_SUPABASE_URL", "").strip() or None
    supabase_service_role_key = os.getenv(
        "AVIA_SUPABASE_SERVICE_ROLE_KEY", ""
    ).strip() or None
    support_email = os.getenv("AVIA_SUPPORT_EMAIL", "").strip() or None
    public_base_url = os.getenv("AVIA_PUBLIC_BASE_URL", "").strip().rstrip("/") or None

    config = RuntimeConfig(
        environment=environment,
        database_url=database_url,
        auth_mode=auth_mode,
        cors_origins=cors_origins,
        jwt_jwks_url=jwt_jwks_url,
        jwt_has_static_key=jwt_has_static_key,
        storage_mode=storage_mode,
        storage_bucket=storage_bucket,
        account_delete_provider=account_delete_provider,
        supabase_url=supabase_url,
        supabase_service_role_key=supabase_service_role_key,
        support_email=support_email,
        public_base_url=public_base_url,
    )
    config.validate()
    return config
