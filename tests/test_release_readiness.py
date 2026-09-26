from types import SimpleNamespace

from release_readiness import build_backend_readiness


class HealthyStore:
    def list_projects(self, owner_id=None):
        return []


class BrokenStore:
    def list_projects(self, owner_id=None):
        raise RuntimeError("database unavailable")


def runtime(**overrides):
    values = {
        "production": True,
        "environment": "production",
        "database_url": "postgresql+psycopg://example/db",
        "auth_mode": "jwt",
        "public_base_url": "https://api.example.com",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_production_readiness_passes_secure_managed_configuration():
    payload, status = build_backend_readiness(
        runtime(),
        HealthyStore(),
        SimpleNamespace(mode="s3"),
    )

    assert status == 200
    assert payload["status"] == "ready"
    assert payload["checks"]["database"] is True
    assert payload["checks"]["authentication"] is True
    assert payload["checks"]["artifact_storage"] is True


def test_readiness_fails_when_database_probe_fails():
    payload, status = build_backend_readiness(
        runtime(),
        BrokenStore(),
        SimpleNamespace(mode="s3"),
    )

    assert status == 503
    assert payload["status"] == "not_ready"
    assert payload["checks"]["database"] is False
    assert payload["database_error"] == "RuntimeError"


def test_production_readiness_rejects_local_artifact_mode():
    payload, status = build_backend_readiness(
        runtime(),
        HealthyStore(),
        SimpleNamespace(mode="local"),
    )

    assert status == 503
    assert payload["checks"]["artifact_storage"] is False


def test_development_readiness_allows_local_auth_and_storage():
    payload, status = build_backend_readiness(
        runtime(
            production=False,
            environment="development",
            database_url=None,
            auth_mode="disabled",
            public_base_url=None,
        ),
        HealthyStore(),
        SimpleNamespace(mode="local"),
    )

    assert status == 200
    assert payload["status"] == "ready"
    assert payload["persistence"] == "sqlite"
