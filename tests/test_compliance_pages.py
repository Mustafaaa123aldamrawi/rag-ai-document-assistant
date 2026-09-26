from compliance_pages import account_deletion_html, privacy_policy_html


def test_privacy_policy_describes_project_data_and_deletion():
    html = privacy_policy_html(
        support_email="support@example.com",
        public_base_url="https://api.example.com",
    )

    assert "Privacy Policy" in html
    assert "Uploaded project content" in html
    assert "drawing analyses" in html.lower()
    assert "account deletion" in html.lower()
    assert "https://api.example.com/account-deletion" in html
    assert "support@example.com" in html


def test_external_account_deletion_page_provides_request_path():
    html = account_deletion_html(
        support_email="support@example.com",
    )

    assert "Delete your AV Intelligence Assistant account" in html
    assert "Delete from the app" in html
    assert "Request deletion outside the app" in html
    assert "mailto:support@example.com" in html
    assert "projects, progress entries, drawing analyses" in html
