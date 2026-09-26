from pathlib import Path

from cloud_store import SqlAlchemyProjectStore


def test_managed_store_supports_full_project_lifecycle(tmp_path: Path):
    db_path = tmp_path / "cloud-test.db"
    store = SqlAlchemyProjectStore(f"sqlite+pysqlite:///{db_path}")

    project = store.create_project(
        name="Production Test",
        owner_id="user-1",
        phase="First Fix",
        location="Riyadh, KSA",
    )

    assert project["owner_id"] == "user-1"
    assert store.get_project(project["id"], owner_id="user-2") is None

    progress = store.add_progress_entry(
        project["id"],
        entry_date="2026-09-26",
        phase="First Fix",
        completed=["Containment inspected"],
        blockers=["Client VLAN pending"],
        next_actions=["Coordinate with IT"],
    )
    assert progress["completed"] == ["Containment inspected"]

    drawing = store.save_drawing_analysis(
        project["id"],
        file_name="drawings.pdf",
        page_count=25,
        register={"sheet_count": 25},
        qa={"finding_count": 1},
        file_hash="abc",
    )
    assert drawing["page_count"] == 25

    report = store.save_report(
        project["id"],
        period="weekly",
        anchor_date="2026-09-26",
        payload={"title": "Weekly AV Project Report"},
    )
    loaded_report = store.get_report(project["id"], report["id"])
    assert loaded_report is not None
    assert loaded_report["payload"]["title"] == "Weekly AV Project Report"

    snapshot = store.project_snapshot(project["id"], owner_id="user-1")
    assert snapshot is not None
    assert len(snapshot["progress_entries"]) == 1
    assert len(snapshot["drawing_analyses"]) == 1
    assert len(snapshot["reports"]) == 1


def test_managed_store_owner_scoping_and_delete(tmp_path: Path):
    db_path = tmp_path / "cloud-test.db"
    store = SqlAlchemyProjectStore(f"sqlite+pysqlite:///{db_path}")

    first = store.create_project(
        name="Owner One",
        owner_id="user-1",
        phase="Design Review / Pre-Start",
    )
    second = store.create_project(
        name="Owner Two",
        owner_id="user-2",
        phase="Design Review / Pre-Start",
    )

    assert [p["id"] for p in store.list_projects(owner_id="user-1")] == [
        first["id"]
    ]
    assert store.delete_project(first["id"], owner_id="user-2") is False
    assert store.delete_project(first["id"], owner_id="user-1") is True
    assert store.get_project(first["id"]) is None
    assert store.get_project(second["id"]) is not None
