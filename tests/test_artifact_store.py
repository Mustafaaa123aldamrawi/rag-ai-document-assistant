from artifact_store import (
    LocalArtifactStore,
    drawing_artifact_key,
    report_artifact_key,
    user_artifact_prefix,
)


def test_local_artifact_store_persists_private_project_bytes(tmp_path):
    store = LocalArtifactStore(tmp_path)
    key = drawing_artifact_key("user-1", "project-1", "Shop Drawing 01.pdf", "abcdef1234567890")
    result = store.put_bytes(
        key=key,
        payload=b"%PDF-test",
        content_type="application/pdf",
    )

    assert result["mode"] == "local"
    assert result["key"] == key
    assert result["size"] == len(b"%PDF-test")
    assert (tmp_path / key).read_bytes() == b"%PDF-test"


def test_artifact_keys_are_user_and_project_scoped():
    drawing = drawing_artifact_key("user@example.com", "p1", "AV Drawing.pdf", "1234567890abcdef")
    report = report_artifact_key("user@example.com", "p1", "weekly", "Weekly Report.docx")

    assert drawing.startswith("users/user_example.com/projects/p1/drawings/")
    assert "AV_Drawing.pdf" in drawing
    assert report == "users/user_example.com/projects/p1/reports/weekly/Weekly_Report.docx"



def test_local_artifact_store_deletes_only_requested_user_prefix(tmp_path):
    store = LocalArtifactStore(tmp_path)
    first_key = drawing_artifact_key(
        "user-1", "p1", "drawing.pdf", "abcdef1234567890"
    )
    second_key = drawing_artifact_key(
        "user-2", "p2", "drawing.pdf", "abcdef1234567890"
    )
    store.put_bytes(
        key=first_key,
        payload=b"one",
        content_type="application/pdf",
    )
    store.put_bytes(
        key=second_key,
        payload=b"two",
        content_type="application/pdf",
    )

    deleted = store.delete_prefix(user_artifact_prefix("user-1"))

    assert deleted == 1
    assert not (tmp_path / first_key).exists()
    assert (tmp_path / second_key).exists()
