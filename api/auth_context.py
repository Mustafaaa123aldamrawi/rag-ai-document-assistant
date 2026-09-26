from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str | None = None


def _mode() -> str:
    return os.getenv("AVIA_AUTH_MODE", "disabled").strip().lower()


def get_current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    mode = _mode()
    if mode == "disabled":
        return AuthUser(id=os.getenv("AVIA_DEV_USER_ID", "local-dev"))

    if mode != "jwt":
        raise HTTPException(status_code=500, detail="Unsupported AVIA_AUTH_MODE.")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    token = authorization.split(" ", 1)[1].strip()
    secret = os.getenv("AVIA_JWT_SECRET")
    public_key = os.getenv("AVIA_JWT_PUBLIC_KEY")
    jwks_url = os.getenv("AVIA_JWT_JWKS_URL")
    key = public_key or secret
    if not key and not jwks_url:
        raise HTTPException(
            status_code=500,
            detail="JWT verification key or JWKS URL is not configured.",
        )

    algorithms = [
        item.strip()
        for item in os.getenv("AVIA_JWT_ALGORITHMS", "HS256").split(",")
        if item.strip()
    ]
    kwargs = {}
    audience = os.getenv("AVIA_JWT_AUDIENCE")
    issuer = os.getenv("AVIA_JWT_ISSUER")
    if audience:
        kwargs["audience"] = audience
    else:
        kwargs["options"] = {"verify_aud": False}
    if issuer:
        kwargs["issuer"] = issuer

    try:
        decode_key = key
        if jwks_url:
            signing_key = PyJWKClient(jwks_url).get_signing_key_from_jwt(token)
            decode_key = signing_key.key
        claims = jwt.decode(token, decode_key, algorithms=algorithms, **kwargs)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired.") from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid bearer token.") from exc

    subject = str(claims.get("sub") or "").strip()
    if not subject:
        raise HTTPException(status_code=401, detail="Token subject is missing.")

    email = claims.get("email")
    return AuthUser(id=subject, email=str(email) if email else None)


def auth_capabilities() -> dict:
    mode = _mode()
    return {
        "mode": mode,
        "production_enforced": mode == "jwt",
        "provider_agnostic": True,
        "jwks_supported": True,
    }