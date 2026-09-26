from __future__ import annotations

from typing import Any


def build_backend_readiness(runtime: Any, store: Any, artifact_store: Any) -> tuple[dict, int]:
    """Return a non-secret readiness summary and HTTP status code.

    The database probe is read-only and owner-scoped. Artifact storage is
    reported by configured mode; object-store connectivity is exercised by the
    real upload path and should not require broad bucket-list permissions.
    """
    checks = {
        "runtime_config": True,
        "database": False,
        "authentication": runtime.auth_mode == "jwt" if runtime.production else True,
        "artifact_storage": (
            getattr(artifact_store, "mode", None) == "s3"
            if runtime.production
            else True
        ),
        "https_public_url": (
            bool(runtime.public_base_url and runtime.public_base_url.startswith("https://"))
            if runtime.production
            else True
        ),
    }
    database_error = None

    try:
        # Works for both SQLite ProjectStore and SqlAlchemyProjectStore.
        store.list_projects(owner_id="__readiness_probe__")
        checks["database"] = True
    except TypeError:
        # Backward-compatible fallback for any local store implementation.
        try:
            store.list_projects()
            checks["database"] = True
        except Exception as exc:  # pragma: no cover - defensive fallback
            database_error = type(exc).__name__
    except Exception as exc:
        database_error = type(exc).__name__

    ready = all(checks.values())
    payload = {
        "status": "ready" if ready else "not_ready",
        "environment": runtime.environment,
        "checks": checks,
        "persistence": "managed_database" if runtime.database_url else "sqlite",
        "auth_mode": runtime.auth_mode,
        "artifact_storage_mode": getattr(artifact_store, "mode", "unknown"),
    }
    if database_error:
        payload["database_error"] = database_error

    return payload, 200 if ready else 503
