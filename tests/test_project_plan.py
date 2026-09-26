from project_plan import build_phase_engineering_plan


def test_first_fix_plan_includes_coordination_and_exit_criteria():
    snapshot = {
        "project": {
            "id": "p1",
            "name": "Pinsent Masons",
            "phase": "First Fix",
        },
        "drawing_analyses": [
            {
                "file_name": "drawings.pdf",
                "page_count": 25,
                "register": {
                    "coordination_requirements": [
                        {
                            "category": "AV power readiness",
                            "requirement": "All AC power at equipment locations.",
                        }
                    ]
                },
                "qa": {
                    "finding_count": 0,
                    "findings": [],
                },
            }
        ],
        "progress_entries": [],
    }

    plan = build_phase_engineering_plan(snapshot)
    assert plan["phase"] == "First Fix"
    assert plan["next_phase"] == "Second Fix / Device Installation"
    assert any("containment" in task.lower() for task in plan["phase_tasks"])
    assert any("AV power readiness" in item for item in plan["recommended_next_actions"])
    assert plan["exit_criteria"]


def test_high_severity_finding_requires_engineering_review():
    snapshot = {
        "project": {
            "id": "p1",
            "name": "Project",
            "phase": "First Fix",
        },
        "drawing_analyses": [
            {
                "file_name": "drawings.pdf",
                "register": {},
                "qa": {
                    "finding_count": 1,
                    "findings": [
                        {
                            "severity": "high",
                            "status": "REVIEW",
                            "category": "direction_conflict",
                            "title": "V0001 appears output-to-output",
                            "recommended_action": "Verify both endpoint ports.",
                        }
                    ],
                },
            }
        ],
        "progress_entries": [],
    }

    plan = build_phase_engineering_plan(snapshot)
    assert plan["readiness"] == "engineering_review_required"
    assert plan["priority_findings"][0]["category"] == "direction_conflict"
    assert "Verify both endpoint ports." in plan["recommended_next_actions"]


def test_blocker_marks_plan_blocked_when_no_high_finding():
    snapshot = {
        "project": {
            "id": "p1",
            "name": "Project",
            "phase": "Second Fix / Device Installation",
        },
        "drawing_analyses": [
            {
                "file_name": "drawings.pdf",
                "register": {},
                "qa": {"finding_count": 0, "findings": []},
            }
        ],
        "progress_entries": [
            {
                "blockers": ["Client network ports not active"],
                "issues": [],
                "completed": [],
                "next_actions": [],
            }
        ],
    }

    plan = build_phase_engineering_plan(snapshot)
    assert plan["readiness"] == "blocked"
    assert "Client network ports not active" in plan["current_blockers"]


def test_programming_without_drawing_requires_drawing_review():
    snapshot = {
        "project": {
            "id": "p1",
            "name": "Project",
            "phase": "Configuration / Programming",
        },
        "drawing_analyses": [],
        "progress_entries": [],
    }

    plan = build_phase_engineering_plan(snapshot)
    assert plan["readiness"] == "drawing_review_required"
    assert plan["drawing_context"]["available"] is False


def test_handover_has_no_next_phase():
    snapshot = {
        "project": {
            "id": "p1",
            "name": "Project",
            "phase": "Handover",
        },
        "drawing_analyses": [],
        "progress_entries": [],
    }

    plan = build_phase_engineering_plan(snapshot)
    assert plan["next_phase"] is None
    assert any("sign-off" in item.lower() for item in plan["exit_criteria"])
