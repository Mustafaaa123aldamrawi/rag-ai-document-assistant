from __future__ import annotations

from datetime import date
from html import escape


def privacy_policy_html(
    *,
    support_email: str | None,
    public_base_url: str | None,
) -> str:
    email = escape(support_email or "Support contact will be published before release.")
    deletion_url = (
        f"{public_base_url.rstrip('/')}/account-deletion"
        if public_base_url
        else "/account-deletion"
    )
    deletion_url = escape(deletion_url)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>AV Intelligence Assistant Privacy Policy</title>
  <style>
    body {{ font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; margin: 0; background:#f8fafc; color:#0f172a; }}
    main {{ max-width: 820px; margin: 0 auto; padding: 40px 22px 70px; }}
    h1,h2 {{ color:#07101d; }} h1 {{ margin-bottom:6px; }}
    p,li {{ line-height:1.65; }} .muted {{ color:#64748b; }}
    a {{ color:#1d4ed8; }}
  </style>
</head>
<body><main>
<h1>AV Intelligence Assistant Privacy Policy</h1>
<p class="muted">Last updated: {date.today().isoformat()}</p>

<p>AV Intelligence Assistant is a professional AV/UC project engineering application.
This policy explains the information processed when you use the service.</p>

<h2>Information we process</h2>
<ul>
  <li><strong>Account information:</strong> authentication identifier, email address, and session information.</li>
  <li><strong>Project information:</strong> project names, locations, client references, lifecycle phase, progress updates, issues, blockers, next actions, and responsible parties entered by users.</li>
  <li><strong>Uploaded project content:</strong> drawings, documents, and other project files that users choose to upload for analysis. Site photos may also be processed when visual inspection features are used.</li>
  <li><strong>Generated engineering content:</strong> drawing registers, QA findings, connection analysis, engineering plans, and project reports created from user-provided project information.</li>
  <li><strong>Technical information:</strong> limited operational and diagnostic information needed to secure, maintain, and troubleshoot the service.</li>
</ul>

<h2>How information is used</h2>
<p>Information is used to authenticate users, isolate projects by account, analyze AV/UC project material, generate reports, provide project tracking, secure the service, and provide support. Project content is not used for advertising.</p>

<h2>Service providers</h2>
<p>The service may use contracted infrastructure and AI service providers for authentication, managed databases, private file storage, AI inference, and optional web-grounded research. Only information required to provide the requested feature is sent to the relevant service.</p>

<h2>Data storage and security</h2>
<p>Production project data is stored in managed infrastructure with account-scoped access controls. Uploaded project artifacts are stored privately. Transport uses HTTPS in production. No security measure can guarantee absolute security, so users should avoid uploading information that is not required for the project workflow.</p>

<h2>Retention and account deletion</h2>
<p>Project information is retained while an account is active or as needed to provide the service. Users can initiate deletion from within the mobile app. Account deletion removes the user's application projects, progress records, drawing analyses, reports, private project artifacts, and authentication account, except information that must be retained for legal or security obligations. Infrastructure backups may persist temporarily according to the applicable provider retention cycle.</p>

<p>Account deletion information and an external deletion request path are available at <a href="{deletion_url}">{deletion_url}</a>.</p>

<h2>Your choices</h2>
<p>You may choose what project material to upload. You can sign out at any time and can request complete account deletion. For privacy questions or deletion assistance, contact <a href="mailto:{email}">{email}</a>.</p>

<h2>Changes</h2>
<p>If this policy changes materially, the public policy will be updated with a new revision date.</p>
</main></body></html>"""


def account_deletion_html(
    *,
    support_email: str | None,
) -> str:
    email = escape(support_email or "Support contact will be published before release.")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Delete AV Intelligence Assistant Account</title>
  <style>
    body {{ font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; margin:0; background:#f8fafc; color:#0f172a; }}
    main {{ max-width:760px; margin:0 auto; padding:44px 22px 70px; }}
    h1,h2 {{ color:#07101d; }} p,li {{ line-height:1.65; }}
    .card {{ background:white; border:1px solid #e2e8f0; border-radius:16px; padding:20px; margin:20px 0; }}
    a {{ color:#1d4ed8; }}
  </style>
</head>
<body><main>
<h1>Delete your AV Intelligence Assistant account</h1>
<p>You can request deletion of your account and associated project data at any time.</p>

<div class="card">
<h2>Delete from the app</h2>
<ol>
  <li>Sign in to AV Intelligence Assistant.</li>
  <li>Open the Account & Privacy section on the Projects screen.</li>
  <li>Select <strong>Delete account</strong>.</li>
  <li>Confirm the deletion request.</li>
</ol>
</div>

<div class="card">
<h2>Request deletion outside the app</h2>
<p>If you cannot access the app, send an account deletion request from the email address associated with your account to <a href="mailto:{email}?subject=AV%20Intelligence%20Assistant%20Account%20Deletion">{email}</a>.</p>
<p>Support may ask you to verify ownership of the account before deletion is completed.</p>
</div>

<h2>Data removed</h2>
<p>Deletion covers the authentication account and application data associated with that account, including projects, progress entries, drawing analyses, generated reports, and private uploaded project artifacts, except information that must be retained for legal or security obligations.</p>
</main></body></html>"""
