from io import BytesIO

from docx import Document

from report_export import build_report_docx, safe_report_filename


def _payload():
    return {
        "report_type": "weekly",
        "title": "Weekly AV Project Report",
        "project": {
            "name": "Pinsent Masons - Riyadh",
            "client": "Pinsent Masons",
            "location": "Riyadh, KSA",
            "phase": "Testing / Commissioning",
            "status": "active",
        },
        "period": {
            "anchor_date": "2026-09-26",
            "date_from": "2026-09-21",
            "date_to": "2026-09-27",
        },
        "executive_summary": {
            "project_health": "verification_required",
            "summary": "Two completed items and one issue were recorded.",
        },
        "progress": {
            "rooms_areas": ["Divisible Meeting Room"],
            "completed": ["Display signal path tested"],
            "in_progress": ["Audio commissioning"],
            "issues_snags": ["Camera framing requires adjustment"],
            "blockers_dependencies": [],
            "next_actions": ["Retest camera preset"],
            "responsible_parties": ["AV Team"],
        },
        "engineering_review": {
            "latest_drawing": {
                "file_name": "shop-drawings.pdf",
                "page_count": 25,
            },
            "connection_graph": {
                "devices": 8,
                "wires": 10,
                "resolved": 9,
                "ambiguous": 1,
                "resolution_percent": 90,
            },
            "visual_reconciliation": {
                "confirmed": 6,
                "conflicts": 1,
                "no_visual_match": 2,
                "visual_only": 1,
            },
            "high_findings": [
                {
                    "severity": "high",
                    "status": "REVIEW",
                    "title": "V0001 endpoint conflict",
                    "why_it_matters": "Text and visual endpoints disagree.",
                    "recommended_action": "Verify both device blocks.",
                }
            ],
        },
        "management_summary": {
            "priority_blockers": [],
            "priority_issues": ["Camera framing requires adjustment"],
            "priority_next_actions": ["Retest camera preset"],
        },
        "handover_readiness": None,
        "quality_statement": "Verify REVIEW items before closure.",
    }


def test_docx_export_is_valid_word_document():
    data = build_report_docx(_payload())

    assert data[:2] == b"PK"
    document = Document(BytesIO(data))
    text = "\n".join(p.text for p in document.paragraphs)

    assert "Weekly AV Project Report" in text
    assert "Executive Summary" in text
    assert "Drawing & Engineering QA" in text
    assert "V0001 endpoint conflict" in text
    assert "Quality Note" in text


def test_final_handover_export_contains_gate():
    payload = _payload()
    payload["report_type"] = "final"
    payload["title"] = "Final AV Handover Report"
    payload["handover_readiness"] = {
        "status": "ready_with_open_items",
        "checks": [
            {"label": "No open project blockers", "passed": True},
            {"label": "No open high-severity engineering findings", "passed": False},
        ],
        "note": "Client acceptance remains required.",
    }

    data = build_report_docx(payload)
    document = Document(BytesIO(data))
    text = "\n".join(p.text for p in document.paragraphs)

    assert "Final AV Handover Report" in text
    assert "Handover Readiness" in text
    assert "READY WITH OPEN ITEMS" in text


def test_safe_report_filename_removes_unsafe_characters():
    payload = {
        "report_type": "weekly",
        "project": {"name": "Client / Riyadh: AV Project"},
    }

    filename = safe_report_filename(payload)

    assert filename.endswith(".docx")
    assert "/" not in filename
    assert ":" not in filename
