from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_render_blueprint_uses_docker_and_health_check():
    source = (ROOT / "render.yaml").read_text(encoding="utf-8")

    assert "runtime: docker" in source
    assert "dockerfilePath: ./Dockerfile" in source
    assert "healthCheckPath: /health" in source
    assert "AVIA_ENV" in source
    assert "value: production" in source


def test_render_blueprint_keeps_sensitive_values_external():
    source = (ROOT / "render.yaml").read_text(encoding="utf-8")

    secret_keys = [
        "AVIA_DATABASE_URL",
        "AVIA_JWT_JWKS_URL",
        "AVIA_STORAGE_BUCKET",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AVIA_SUPABASE_SERVICE_ROLE_KEY",
        "HF_TOKEN",
    ]
    for key in secret_keys:
        block_start = source.index(f"- key: {key}")
        following = source[block_start : block_start + 120]
        assert "sync: false" in following


def test_production_env_template_contains_required_cloud_contract():
    source = (ROOT / ".env.production.example").read_text(encoding="utf-8")

    for key in (
        "AVIA_DATABASE_URL",
        "AVIA_JWT_JWKS_URL",
        "AVIA_JWT_ALGORITHMS",
        "AVIA_STORAGE_MODE=s3",
        "AVIA_STORAGE_BUCKET",
        "AVIA_ACCOUNT_DELETE_PROVIDER=supabase",
        "AVIA_SUPABASE_URL",
        "AVIA_SUPABASE_SERVICE_ROLE_KEY",
        "AVIA_SUPPORT_EMAIL",
        "AVIA_PUBLIC_BASE_URL",
    ):
        assert key in source

    assert "localhost" not in source.lower()
    assert "127.0.0.1" not in source


def test_production_smoke_checker_verifies_core_services():
    source = (
        ROOT / "scripts" / "production_smoke_check.py"
    ).read_text(encoding="utf-8")

    assert "production_environment" in source
    assert "managed_database" in source
    assert "jwt_auth" in source
    assert "private_cloud_storage" in source
    assert '"/privacy"' in source
    assert '"/account-deletion"' in source
