from __future__ import annotations

import os
from urllib.parse import quote

import requests


class AccountDeletionError(RuntimeError):
    pass


def deletion_provider() -> str:
    return os.getenv("AVIA_ACCOUNT_DELETE_PROVIDER", "disabled").strip().lower()


def delete_auth_identity(user_id: str, *, timeout: int = 20) -> dict:
    """Delete the authenticated identity from the configured auth provider.

    Development defaults to disabled so local tests do not call an external
    identity provider. Production configuration validation requires a real
    provider.
    """
    provider = deletion_provider()
    if provider == "disabled":
        return {
            "provider": provider,
            "identity_deleted": False,
            "development_only": True,
        }

    if provider != "supabase":
        raise AccountDeletionError(
            f"Unsupported account deletion provider: {provider}"
        )

    base_url = os.getenv("AVIA_SUPABASE_URL", "").strip().rstrip("/")
    service_key = os.getenv(
        "AVIA_SUPABASE_SERVICE_ROLE_KEY", ""
    ).strip()
    if not base_url or not service_key:
        raise AccountDeletionError(
            "Supabase account deletion is not configured."
        )

    response = requests.delete(
        f"{base_url}/auth/v1/admin/users/{quote(str(user_id), safe='')}",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
        },
        timeout=timeout,
    )

    if response.status_code not in {200, 204}:
        raise AccountDeletionError(
            "Auth provider rejected account deletion "
            f"(HTTP {response.status_code})."
        )

    return {
        "provider": provider,
        "identity_deleted": True,
    }
