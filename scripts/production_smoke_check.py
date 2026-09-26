from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def _read(url: str, *, json_response: bool = False, timeout: int = 20):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "avia-deployment-smoke-check/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
        if json_response:
            return response.status, json.loads(payload.decode("utf-8"))
        return response.status, payload


def main() -> int:
    base_url = os.getenv("AVIA_SMOKE_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        print("AVIA_SMOKE_BASE_URL is required.", file=sys.stderr)
        return 2
    if not base_url.startswith("https://"):
        print("Production smoke checks require HTTPS.", file=sys.stderr)
        return 2

    checks: dict[str, bool] = {}
    try:
        status, health = _read(f"{base_url}/health", json_response=True)
    except (urllib.error.URLError, ValueError, json.JSONDecodeError) as exc:
        print(f"Health check failed: {exc}", file=sys.stderr)
        return 1

    checks["health_http_200"] = status == 200
    checks["status_ok"] = health.get("status") == "ok"
    checks["production_environment"] = health.get("environment") == "production"
    checks["managed_database"] = health.get("persistence") == "managed_database"
    checks["jwt_auth"] = (
        (health.get("auth") or {}).get("production_enforced") is True
    )

    for path in ("/privacy", "/account-deletion"):
        try:
            status, payload = _read(f"{base_url}{path}")
            checks[f"public_page_{path}"] = status == 200 and bool(payload)
        except urllib.error.URLError:
            checks[f"public_page_{path}"] = False

    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")

    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
