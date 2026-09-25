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
                    "Manufacturer and model are not readable."
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
    assert summary["inspection_meta"]["overall_status"] == "ACTION REQUIRED"
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
    assert len(merged["inspection_sections"]) == 2
    assert merged["inspection_sections"][0]["section_title"] == "Scope Verification"
    assert merged["inspection_sections"][1]["section_title"] == "Visual Evidence / Site Findings"
    assert merged["visual_findings"]
