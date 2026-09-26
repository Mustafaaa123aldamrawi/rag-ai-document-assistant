from datetime import date

from professional_reports import (
    build_professional_project_report,
    render_professional_report_markdown,
)


def _snapshot():
    return {
        "project": {
            "id": "p1",
            "name": "Pinsent Masons - Riyadh",
            "client": "Pinsent Masons",
            "location": "Riyadh, KSA",
            "opportunity_number": "390I-25-88927",
            "phase": "Testing / Commissioning",
            "status": "active",
        },
        "progress_entries": [
            {
                "date": "2026-09-24",
                "phase": "Testing / Commissioning",
                "rooms": ["Divisible Meeting Room"],
                "completed": ["Display signal path tested"],
                "in_progress": ["Audio commissioning"],
                "issues": ["Room 2 camera framing requires adjustment"],
                "blockers": [],
                "next_actions": ["Retest camera preset"],
                "responsible_parties": ["AV Team"],
            },
            {
                "date": "2026-09-25",
                "phase": "Testing / Commissioning",
                "rooms": ["Divisible Meeting Room"],
                "completed": ["Partition sensor logic tested"],
                "in_progress": [],
                "issues": [],
                "blockers": ["Client VLAN not active"],
                "next_actions": ["Coordinate VLAN activation with IT"],
                "responsible_parties": ["IT"],
            },
        ],
        "drawing_analyses": [
            {
                "id": "d1",
                "file_name": "shop-drawings.pdf",
                "page_count": 25,
                "created_at": "2026-09-23T10:00:00Z",
                "qa": {
                    "findings": [
                        {
                            "severity": "high",
                            "status": "REVIEW",
                            "title": "V0001 endpoint conflict",
                            "recommended_action": "Verify both endpoints.",
                        }
                    ],
                    "connection_graph": {
                        "node_count": 8,
                        "edge_count": 10,
                        "resolved_edge_count": 9,
                        "ambiguous_edge_count": 1,
                        "resolution_rate": 0.9,
                    },
                    "visual_reconciliation": {
                        "confirmed_count": 6,
                        "conflict_count": 1,
                        "no_visual_match_count": 2,
                        "visual_only_count": 1,
                    },
                },
            }
        ],
        "reports": [],
    }


def test_weekly_professional_report_combines_progress_and_engineering():
    report = build_professional_project_report(
        _snapshot(),
        period="weekly",
        anchor_date=date(2026, 9, 25),
    )

    assert report["schema_version"] == 2
    assert report["title"] == "Weekly AV Project Report"
    assert report["project"]["name"] == "Pinsent Masons - Riyadh"
    assert report["period"]["entries_count"] == 2
    assert "Display signal path tested" in report["progress"]["completed"]
    assert "Client VLAN not active" in report["progress"]["blockers_dependencies"]
    assert report["engineering_review"]["connection_graph"]["resolution_percent"] == 90
    assert report["engineering_review"]["visual_reconciliation"]["confirmed"] == 6
    assert len(report["engineering_review"]["high_findings"]) == 1
    assert "Weekly AV Project Report" in report["markdown"]


def test_daily_report_filters_entries_to_anchor_date():
    report = build_professional_project_report(
        _snapshot(),
        period="daily",
        anchor_date=date(2026, 9, 25),
    )

    assert report["period"]["entries_count"] == 1
    assert report["progress"]["completed"] == ["Partition sensor logic tested"]
    assert report["progress"]["issues_snags"] == []
    assert report["progress"]["blockers_dependencies"] == ["Client VLAN not active"]


def test_final_handover_report_uses_all_history_and_gate():
    snapshot = _snapshot()
    snapshot["project"]["phase"] = "Handover"

    report = build_professional_project_report(
        snapshot,
        period="final",
        anchor_date=date(2026, 9, 26),
    )

    assert report["title"] == "Final AV Handover Report"
    assert report["period"]["entries_count"] == 2
    assert report["handover_readiness"] is not None
    assert report["handover_readiness"]["status"] == "not_ready"
    failed_ids = {
        item["id"] for item in report["handover_readiness"]["failed_checks"]
    }
    assert "no_blockers" in failed_ids
    assert "no_high_findings" in failed_ids
    assert "connection_graph_reviewed" in failed_ids
    assert "visual_conflicts_closed" in failed_ids


def test_handover_gate_can_reach_ready_for_review():
    snapshot = _snapshot()
    snapshot["project"]["phase"] = "Handover"
    snapshot["progress_entries"] = [
        {
            "date": "2026-09-25",
            "phase": "Handover",
            "completed": ["Client training complete"],
            "issues": [],
            "blockers": [],
            "next_actions": ["Obtain final client signature"],
        }
    ]
    qa = snapshot["drawing_analyses"][0]["qa"]
    qa["findings"] = []
    qa["connection_graph"]["ambiguous_edge_count"] = 0
    qa["connection_graph"]["resolution_rate"] = 1.0
    qa["visual_reconciliation"]["conflict_count"] = 0

    report = build_professional_project_report(
        snapshot,
        period="final",
        anchor_date=date(2026, 9, 26),
    )

    assert report["handover_readiness"]["status"] == "ready_for_handover_review"
    assert report["handover_readiness"]["failed_checks"] == []


def test_markdown_contains_client_facing_sections():
    report = build_professional_project_report(
        _snapshot(),
        period="monthly",
        anchor_date=date(2026, 9, 25),
    )
    markdown = render_professional_report_markdown(report)

    assert "## Executive Summary" in markdown
    assert "## Issues / Snags" in markdown
    assert "## Drawing & Engineering QA" in markdown
    assert "## Quality Note" in markdown
