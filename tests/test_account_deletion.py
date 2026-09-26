import account_deletion


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_disabled_account_delete_provider_is_safe_for_local_development(monkeypatch):
    monkeypatch.delenv("AVIA_ACCOUNT_DELETE_PROVIDER", raising=False)
    result = account_deletion.delete_auth_identity("user-1")

    assert result["provider"] == "disabled"
    assert result["identity_deleted"] is False
    assert result["development_only"] is True


def test_supabase_account_deletion_uses_admin_endpoint(monkeypatch):
    calls = []

    def fake_delete(url, headers, timeout):
        calls.append((url, headers, timeout))
        return FakeResponse(204)

    monkeypatch.setenv("AVIA_ACCOUNT_DELETE_PROVIDER", "supabase")
    monkeypatch.setenv("AVIA_SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("AVIA_SUPABASE_SERVICE_ROLE_KEY", "service-role")
    monkeypatch.setattr(account_deletion.requests, "delete", fake_delete)

    result = account_deletion.delete_auth_identity("user/123")

    assert result["identity_deleted"] is True
    assert calls[0][0].endswith("/auth/v1/admin/users/user%2F123")
    assert calls[0][1]["Authorization"] == "Bearer service-role"
    assert calls[0][1]["apikey"] == "service-role"


def test_supabase_account_deletion_failure_is_explicit(monkeypatch):
    monkeypatch.setenv("AVIA_ACCOUNT_DELETE_PROVIDER", "supabase")
    monkeypatch.setenv("AVIA_SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("AVIA_SUPABASE_SERVICE_ROLE_KEY", "service-role")
    monkeypatch.setattr(
        account_deletion.requests,
        "delete",
        lambda *args, **kwargs: FakeResponse(500),
    )

    try:
        account_deletion.delete_auth_identity("user-1")
        assert False, "Expected AccountDeletionError"
    except account_deletion.AccountDeletionError as exc:
        assert "HTTP 500" in str(exc)
