from project_dashboard import build_project_dashboard


def test_dashboard_marks_high_finding_as_engineering_review():
    snapshot = {
        "project": {
            "id": "p1",
            "name": "Project",
            "phase": "First Fix",
            "status": "active",
        },
        "progress_entries": [],
        "reports": [],
        "drawing_analyses": [
            {
                "id": "d1",
                "file_name": "drawings.pdf",
                "page_count": 25,
                "qa": {
                    "findings": [
                        {
                            "severity": "high",
                            "status": "REVIEW",
                            "title": "Output-to-output connection",
                        }
                    ],
                    "connection_graph": {
                        "node_count": 4,
                        "edge_count": 3,
                        "resolved_edge_count": 2,
                        "ambiguous_edge_count": 1,
                        "resolution_rate": 2 / 3,
                    },
                },
            }
        ],
    }

    dashboard = build_project_dashboard(snapshot)

    assert dashboard["health"] == "engineering_review_required"
    assert dashboard["kpis"]["high_findings"] == 1
    assert dashboard["kpis"]["graph_resolution_percent"] == 67
    assert dashboard["phase"]["next_phase"] == "Second Fix / Device Installation"


def test_dashboard_prioritizes_blockers_and_next_actions():
    snapshot = {
        "project": {
            "id": "p1",
            "name": "Project",
            "phase": "Second Fix / Device Installation",
            "status": "active",
        },
        "drawing_analyses": [{"qa": {"findings": []}}],
        "reports": [],
        "progress_entries": [
            {
                "date": "2026-09-26",
                "completed": ["Display installed"],
                "issues": ["Camera bracket missing"],
                "blockers": ["Client VLAN not ready"],
                "next_actions": ["Install camera after bracket delivery"],
            }
        ],
    }

    dashboard = build_project_dashboard(snapshot)

    assert dashboard["health"] == "blocked"
    assert dashboard["kpis"]["open_blockers"] == 1
    assert dashboard["priority"]["blockers"] == ["Client VLAN not ready"]
    assert dashboard["latest_update"]["date"] == "2026-09-26"


def test_dashboard_includes_visual_reconciliation_kpis():
    snapshot = {
        "project": {
            "id": "p1",
            "name": "Project",
            "phase": "Design Review / Pre-Start",
            "status": "active",
        },
        "progress_entries": [],
        "reports": [],
        "drawing_analyses": [
            {
                "qa": {
                    "findings": [],
                    "connection_graph": {},
                    "visual_reconciliation": {
                        "confirmed_count": 7,
                        "conflict_count": 2,
                    },
                }
            }
        ],
    }

    dashboard = build_project_dashboard(snapshot)

    assert dashboard["kpis"]["visual_confirmed_connections"] == 7
    assert dashboard["kpis"]["visual_conflicts"] == 2
    assert dashboard["kpis"]["visual_reviewed_connections"] == 9


def test_dashboard_without_drawing_requires_review():
    snapshot = {
        "project": {
            "id": "p1",
            "name": "Project",
            "phase": "Design Review / Pre-Start",
            "status": "active",
        },
        "progress_entries": [],
        "reports": [],
        "drawing_analyses": [],
    }

    dashboard = build_project_dashboard(snapshot)

    assert dashboard["health"] == "drawing_review_required"
    assert dashboard["latest_drawing"] is None
