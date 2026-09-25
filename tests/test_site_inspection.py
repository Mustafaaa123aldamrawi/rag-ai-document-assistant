from pathlib import Path
from site_inspection import (
    build_inspection_only_survey_data,
    build_site_inspection_summary,
    merge_site_inspection_into_survey_data,
)


def sample_visual_items():
    return [
        {
            "file_name": "display.jpg",
            "analysis": {
                "category": "SITE_PHOTO",
                "summary": "A curved display is active.",
                "visible_text": [],
                "devices": [],
                "observations": [
                    "A curved display is active and showing a desktop."
                ],
                "possible_issues": [],
                "uncertainties": [
                    "The cable destination cannot be confirmed from the visible area."
                ],
            },
        },
        {
            "file_name": "rack.jpg",
            "analysis": {
                "category": "AV_EQUIPMENT",
                "summary": "Rack equipment is visible.",
                "visible_text": [],
                "devices": [],
                "observations": [
                    "Rack-mounted equipment is visible."
                ],
                "possible_issues": [
                    {
                        "issue": "A visible cable appears partially disconnected.",
                        "confidence": "medium",
                        "basis": "The connector is visibly not fully seated.",
                    }
                ],
                "uncertainties": [],
            },
        },
    ]


def test_multi_image_summary_aggregates_photos_findings_and_verify_items():
    summary = build_site_inspection_summary(sample_visual_items())

    assert summary["inspection_meta"]["photos_reviewed"] == 2
    assert summary["inspection_meta"]["possible_issues"] == 1
    assert summary["inspection_meta"]["verify_items"] == 1
    assert summary["inspection_meta"]["overall_status"] == "REVIEW REQUIRED"
    assert len(summary["photo_register"]) == 2
    assert summary["visual_findings"][0]["source_photo"] == "rack.jpg"


def test_inspection_only_data_is_report_compatible():
    summary = build_site_inspection_summary(sample_visual_items())
    data = build_inspection_only_survey_data(summary)

    assert data["project_info"]["project_name"] == "AV/UC Site Inspection"
    assert data["checklist_sections"]
    assert data["photo_register"]
    assert data["visual_inspection"]["inspection_meta"]["photos_reviewed"] == 2


def test_merge_preserves_scope_inspection_sections():
    base = {
        "project_info": {
            "project_name": "Project X",
            "rooms": ["Room-1"],
        },
        "inspection_sections": [
            {
                "section_number": 1,
                "section_title": "Scope Verification",
                "items": [
                    {
                        "item_number": 1,
                        "inspection_item": "Verify display location",
                        "status": "VERIFY",
                        "status_options": ["YES", "NO", "N/A"],
                        "notes_photo": "",
                    }
                ],
            }
        ],
        "photo_register": [],
    }

    summary = build_site_inspection_summary(sample_visual_items())
    merged = merge_site_inspection_into_survey_data(base, summary)

    assert "checklist_sections" not in merged
    assert len(merged["inspection_sections"]) == 1
    assert merged["inspection_sections"][0]["section_title"] == "Scope Verification"
    assert merged["visual_findings"]



def test_multi_image_summary_filters_low_value_verify_noise_and_caps_per_photo():
    items = [
        {
            "file_name": "room.jpg",
            "analysis": {
                "category": "SITE_PHOTO",
                "summary": "Meeting room visible.",
                "visible_text": [],
                "devices": [],
                "observations": ["Meeting room visible."],
                "possible_issues": [],
                "uncertainties": [
                    "Manufacturer and model are not readable.",
                    "Exact labels are not fully readable.",
                    "Partition sensor location requires site verification.",
                    "Cable route above the ceiling requires site verification.",
                    "Another unrelated uncertain detail.",
                ],
            },
        }
    ]

    summary = build_site_inspection_summary(items)
    assert summary["inspection_meta"]["verify_items"] == 2
    verify_text = " ".join(
        item["item"] for item in summary["verification_items"]
    ).lower()
    assert "manufacturer and model" not in verify_text
    assert "exact labels" not in verify_text


def test_high_confidence_noncritical_finding_is_observation_not_action():
    items = [
        {
            "file_name": "rack.jpg",
            "analysis": {
                "category": "AV_EQUIPMENT",
                "summary": "Rack visible.",
                "visible_text": [],
                "devices": [],
                "observations": ["Rack visible."],
                "possible_issues": [
                    {
                        "issue": "A connector appears partially seated.",
                        "confidence": "high",
                        "basis": "Visible connector position.",
                    }
                ],
                "uncertainties": [],
            },
        }
    ]

    summary = build_site_inspection_summary(items)
    assert summary["inspection_meta"]["overall_status"] == "REVIEW REQUIRED"
    assert summary["visual_findings"][0]["status"] == "OBSERVATION"


def test_high_confidence_safety_finding_can_hold():
    items = [
        {
            "file_name": "ceiling.jpg",
            "analysis": {
                "category": "SITE_PHOTO",
                "summary": "Ceiling area visible.",
                "visible_text": [],
                "devices": [],
                "observations": ["Overhead area visible."],
                "possible_issues": [
                    {
                        "issue": "An exposed live electrical conductor is visible.",
                        "confidence": "high",
                        "basis": "Bare energized conductor is visibly exposed.",
                    }
                ],
                "uncertainties": [],
            },
        }
    ]

    summary = build_site_inspection_summary(items)
    assert summary["inspection_meta"]["overall_status"] == "ACTION REQUIRED"
    assert summary["visual_findings"][0]["status"] == "ACTION"



def test_photo_register_uses_short_photo_refs():
    summary = build_site_inspection_summary(sample_visual_items())
    assert summary["photo_register"][0]["photo_ref"] == "P01"
    assert summary["photo_register"][1]["photo_ref"] == "P02"
    assert summary["visual_findings"][0]["source_photo_ref"] == "P02"


def test_scope_merge_does_not_duplicate_visual_findings_into_scope_sections():
    base = {
        "project_info": {"project_name": "Project X", "rooms": ["Room-1"]},
        "inspection_sections": [
            {
                "section_number": 1,
                "section_title": "System design intent",
                "items": [
                    {
                        "item_number": 1,
                        "inspection_item": "Verify divisible room operation.",
                        "status": "VERIFY",
                        "status_options": ["PASS", "VERIFY", "ACTION", "N/A"],
                        "notes_photo": "",
                    }
                ],
            }
        ],
        "photo_register": [],
    }
    summary = build_site_inspection_summary(sample_visual_items())
    merged = merge_site_inspection_into_survey_data(base, summary)

    assert len(merged["inspection_sections"]) == 1
    assert merged["inspection_sections"][0]["section_title"] == "System design intent"
    assert merged["visual_findings"]



def test_app_builds_project_specific_scope_sections():
    app_source = (
        Path(__file__).resolve().parents[1] / "app.py"
    ).read_text(encoding="utf-8")

    assert '"Existing equipment to retain / reuse"' in app_source
    assert '"New equipment / installation verification"' in app_source
    assert '"System design intent"' in app_source
    assert '"Equipment relocations"' in app_source
    assert '"Equipment removal / decommissioning"' in app_source
    assert '"Project-specific integration checks"' in app_source
