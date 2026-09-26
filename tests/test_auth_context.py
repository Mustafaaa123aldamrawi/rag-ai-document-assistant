import os
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from api.auth_context import get_current_user


def _set_jwt_env(monkeypatch):
    monkeypatch.setenv("AVIA_AUTH_MODE", "jwt")
    monkeypatch.setenv("AVIA_JWT_SECRET", "test-secret")
    monkeypatch.setenv("AVIA_JWT_ALGORITHMS", "HS256")
    monkeypatch.delenv("AVIA_JWT_AUDIENCE", raising=False)
    monkeypatch.delenv("AVIA_JWT_ISSUER", raising=False)


def test_disabled_auth_uses_local_dev_identity(monkeypatch):
    monkeypatch.setenv("AVIA_AUTH_MODE", "disabled")
    monkeypatch.setenv("AVIA_DEV_USER_ID", "dev-user")
    user = get_current_user(None)
    assert user.id == "dev-user"


def test_valid_jwt_returns_subject(monkeypatch):
    _set_jwt_env(monkeypatch)
    token = jwt.encode(
        {
            "sub": "user-123",
            "email": "engineer@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        "test-secret",
        algorithm="HS256",
    )
    user = get_current_user(f"Bearer {token}")
    assert user.id == "user-123"
    assert user.email == "engineer@example.com"


def test_missing_token_is_rejected_when_auth_enabled(monkeypatch):
    _set_jwt_env(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        get_current_user(None)
    assert exc.value.status_code == 401


def test_expired_token_is_rejected(monkeypatch):
    _set_jwt_env(monkeypatch)
    token = jwt.encode(
        {
            "sub": "user-123",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        "test-secret",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        get_current_user(f"Bearer {token}")
    assert exc.value.status_code == 401