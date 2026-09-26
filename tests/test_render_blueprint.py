from pathlib import Path


def test_render_blueprint_uses_production_docker_and_readiness():
    source = (Path(__file__).resolve().parents[1] / "render.yaml").read_text(
        encoding="utf-8"
    )

    assert "runtime: docker" in source
    assert "dockerfilePath: ./Dockerfile" in source
    assert "healthCheckPath: /ready" in source
    assert "key: AVIA_ENV" in source
    assert "value: production" in source
    assert "key: AVIA_DATABASE_URL" in source
    assert "key: AVIA_SUPABASE_SERVICE_ROLE_KEY" in source
    assert "key: AVIA_STORAGE_BUCKET" in source


def test_render_blueprint_does_not_commit_production_secrets():
    source = (Path(__file__).resolve().parents[1] / "render.yaml").read_text(
        encoding="utf-8"
    )

    for key in (
        "AVIA_DATABASE_URL",
        "AVIA_JWT_JWKS_URL",
        "AVIA_SUPABASE_SERVICE_ROLE_KEY",
        "HF_TOKEN",
    ):
        section = source.split(f"key: {key}", 1)[1].split("- key:", 1)[0]
        assert "sync: false" in section
