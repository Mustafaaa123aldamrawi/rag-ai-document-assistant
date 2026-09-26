from pathlib import Path

from project_store import ProjectStore


def test_project_store_persists_project_and_progress(tmp_path: Path):
    db_path = tmp_path / "project.db"
    store = ProjectStore(db_path)

    project = store.create_project(
        name="Pinsent Masons - Riyadh",
        location="Riyadh, KSA",
        client="Pinsent Masons",
        opportunity_number="390I-25-88927",
        phase="First Fix",
    )

    entry = store.add_progress_entry(
        project["id"],
        entry_date="2026-09-26",
        phase="First Fix",
        rooms=["L7-07 Client Meeting 03"],
        completed=["Containment checked"],
        issues=["Data outlet not ready"],
        blockers=["Awaiting IT"],
        next_actions=["Pull AV cabling after data outlet readiness"],
        responsible_parties=["IT"],
    )

    assert entry["project_id"] == project["id"]
    assert entry["issues"] == ["Data outlet not ready"]

    # Re-open a fresh store instance to prove persistence is not session memory.
    reopened = ProjectStore(db_path)
    snapshot = reopened.project_snapshot(project["id"])

    assert snapshot is not None
    assert snapshot["project"]["name"] == "Pinsent Masons - Riyadh"
    assert snapshot["project"]["phase"] == "First Fix"
    assert len(snapshot["progress_entries"]) == 1
    assert snapshot["progress_entries"][0]["blockers"] == ["Awaiting IT"]


def test_project_store_drawing_and_report_history(tmp_path: Path):
    store = ProjectStore(tmp_path / "project.db")
    project = store.create_project(
        name="AV Project",
        phase="Design Review / Pre-Start",
    )

    drawing = store.save_drawing_analysis(
        project["id"],
        file_name="shop-drawings.pdf",
        file_hash="abc123",
        page_count=25,
        register={"sheet_count": 25},
        qa={"finding_count": 2},
    )
    report = store.save_report(
        project["id"],
        period="weekly",
        anchor_date="2026-09-26",
        payload={"title": "Weekly Progress Report"},
    )

    reopened = ProjectStore(tmp_path / "project.db")
    drawings = reopened.list_drawing_analyses(project["id"])
    reports = reopened.list_reports(project["id"])

    assert drawings[0]["id"] == drawing["id"]
    assert drawings[0]["register"]["sheet_count"] == 25
    assert drawings[0]["qa"]["finding_count"] == 2
    assert reports[0]["id"] == report["id"]
    assert reports[0]["payload"]["title"] == "Weekly Progress Report"


def test_project_store_delete_cascades_related_records(tmp_path: Path):
    store = ProjectStore(tmp_path / "project.db")
    project = store.create_project(name="Delete Me", phase="Handover")
    store.add_progress_entry(
        project["id"],
        entry_date="2026-09-26",
        completed=["Client sign-off received"],
    )
    store.save_report(
        project["id"],
        period="daily",
        anchor_date="2026-09-26",
        payload={"status": "done"},
    )

    assert store.delete_project(project["id"]) is True
    assert store.get_project(project["id"]) is None
    assert store.list_progress_entries(project["id"]) == []
    assert store.list_reports(project["id"]) == []


def test_project_store_date_filters(tmp_path: Path):
    store = ProjectStore(tmp_path / "project.db")
    project = store.create_project(name="Filter Test", phase="First Fix")
    for day in ("2026-09-24", "2026-09-25", "2026-09-26"):
        store.add_progress_entry(
            project["id"],
            entry_date=day,
            completed=[f"Work {day}"],
        )

    entries = store.list_progress_entries(
        project["id"],
        start_date="2026-09-25",
        end_date="2026-09-26",
    )

    assert [entry["date"] for entry in entries] == [
        "2026-09-25",
        "2026-09-26",
    ]



def test_project_store_isolates_projects_by_owner(tmp_path: Path):
    store = ProjectStore(tmp_path / "project.db")
    alpha = store.create_project(
        name="Alpha Project",
        phase="First Fix",
        owner_id="user-alpha",
    )
    beta = store.create_project(
        name="Beta Project",
        phase="First Fix",
        owner_id="user-beta",
    )

    alpha_projects = store.list_projects(owner_id="user-alpha")
    beta_projects = store.list_projects(owner_id="user-beta")

    assert [item["id"] for item in alpha_projects] == [alpha["id"]]
    assert [item["id"] for item in beta_projects] == [beta["id"]]
    assert store.get_project(beta["id"], owner_id="user-alpha") is None
    assert store.delete_project(beta["id"], owner_id="user-alpha") is False
    assert store.get_project(beta["id"], owner_id="user-beta") is not None


def test_project_store_migrates_existing_database_with_local_owner(tmp_path: Path):
    import sqlite3

    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT,
            client TEXT,
            opportunity_number TEXT,
            phase TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO projects(
            id, name, phase, status, metadata_json, created_at, updated_at
        ) VALUES('legacy-1', 'Legacy', 'First Fix', 'active', '{}', 'x', 'x')
        """
    )
    conn.commit()
    conn.close()

    store = ProjectStore(db_path)
    migrated = store.get_project("legacy-1")

    assert migrated is not None
    assert migrated["owner_id"] == "local-dev"
