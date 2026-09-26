import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mobile_store_identifiers_and_versions_are_pinned():
    config = json.loads((ROOT / "mobile" / "app.json").read_text())
    expo = config["expo"]

    assert expo["ios"]["bundleIdentifier"] == "com.avintelligence.assistant"
    assert expo["android"]["package"] == "com.avintelligence.assistant"
    assert int(expo["android"]["versionCode"]) >= 1
    assert int(expo["ios"]["buildNumber"]) >= 1
    assert expo["runtimeVersion"]["policy"] == "appVersion"


def test_eas_production_build_targets_stores_and_auto_increments():
    config = json.loads((ROOT / "mobile" / "eas.json").read_text())
    production = config["build"]["production"]

    assert production["distribution"] == "store"
    assert production["channel"] == "production"
    assert production["autoIncrement"] is True
    assert config["cli"]["appVersionSource"] == "remote"


def test_production_mobile_config_fails_closed():
    source = (ROOT / "mobile" / "app.config.js").read_text()

    assert "EXPO_PUBLIC_API_URL" in source
    assert "EXPO_PUBLIC_SUPABASE_URL" in source
    assert "EXPO_PUBLIC_SUPABASE_ANON_KEY" in source
    assert "localhost" in source
    assert "127.0.0.1" in source


def test_production_api_container_uses_lean_requirements():
    dockerfile = (ROOT / "Dockerfile").read_text()
    requirements = (ROOT / "requirements-api.txt").read_text()

    assert "requirements-api.txt" in dockerfile
    assert "uvicorn" in dockerfile
    assert "api.main:app" in dockerfile
    assert "boto3" in requirements
    assert "psycopg" in requirements
    assert "streamlit" not in requirements.lower()
