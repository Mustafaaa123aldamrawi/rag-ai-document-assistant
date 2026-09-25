from pathlib import Path
from site_inspection import (
    build_inspection_only_survey_data,
    build_site_inspection_summary,
    derive_survey_status,
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
    assert summary["inspection_meta"]["verify_items"] == 0
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
    assert summary["inspection_meta"]["verify_items"] == 0
    assert summary["verification_items"] == []


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



def test_scope_verify_status_is_separate_from_no_visual_fault():
    base = {
        "inspection_sections": [
            {
                "section_title": "Scope",
                "items": [
                    {
                        "inspection_item": "Verify partition sensor",
                        "status": "VERIFY",
                    }
                ],
            }
        ]
    }
    summary = {
        "inspection_meta": {
            "overall_status": "NO OBVIOUS VISUAL FAULT",
            "visual_status": "NO OBVIOUS VISUAL FAULT",
            "actions": 0,
            "observations": 0,
            "verify_items": 0,
        }
    }
    assert derive_survey_status(base, summary) == "FIELD VERIFICATION REQUIRED"


def test_merge_keeps_visual_and_survey_status_separate():
    base = {
        "project_info": {"project_name": "Mastercard Riyadh"},
        "inspection_sections": [
            {
                "section_title": "Project-specific integration checks",
                "items": [
                    {
                        "inspection_item": "Verify Dante path",
                        "status": "VERIFY",
                    }
                ],
            }
        ],
    }
    summary = {
        "inspection_meta": {
            "overall_status": "NO OBVIOUS VISUAL FAULT",
            "visual_status": "NO OBVIOUS VISUAL FAULT",
            "photos_reviewed": 1,
            "possible_issues": 0,
            "observations": 0,
            "actions": 0,
            "verify_items": 0,
        },
        "executive_summary": "One photo reviewed.",
        "photo_register": [],
        "visual_findings": [],
        "verification_items": [],
    }
    merged = merge_site_inspection_into_survey_data(base, summary)
    assert merged["visual_status"] == "NO OBVIOUS VISUAL FAULT"
    assert merged["survey_status"] == "FIELD VERIFICATION REQUIRED"


def test_app_persists_inspection_photos_and_has_clear_control():
    app_source = (
        Path(__file__).resolve().parents[1] / "app.py"
    ).read_text(encoding="utf-8")
    assert '"site_inspection_photo_registry"' in app_source
    assert '"🧹 Clear Inspection Photos"' in app_source
    assert '"site_inspection_photo_registry"' in app_source
    assert "visual_cache_key] = visual_item" in app_source


def test_app_deduplicates_equipment_identity_components():
    app_source = (
        Path(__file__).resolve().parents[1] / "app.py"
    ).read_text(encoding="utf-8")
    assert "def format_equipment_identity(equipment):" in app_source
    assert "if value.lower() in identity.lower():" in app_source



def test_low_value_model_and_room_uncertainties_are_filtered():
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
                    "The exact Crestron model number is not visible on the device.",
                    "The exact function of the space (meeting room, training room, open workspace) is not labeled and is inferred only from furniture.",
                    "The make/model and power state of the background flat-panel screen are not visible.",
                ],
            },
        }
    ]
    summary = build_site_inspection_summary(items)
    assert summary["verification_items"] == []
    assert summary["inspection_meta"]["verify_items"] == 0


def test_scope_items_receive_relevant_photo_refs():
    base = {
        "project_info": {"project_name": "Project X"},
        "inspection_sections": [
            {
                "section_title": "Existing equipment to retain / reuse",
                "items": [
                    {
                        "inspection_item": "Verify retained Crestron Room Scheduling Touch Panel",
                        "status": "VERIFY",
                    },
                    {
                        "inspection_item": "Verify existing rack capacity and PDU",
                        "status": "VERIFY",
                    },
                ],
            }
        ],
    }
    summary = {
        "inspection_meta": {
            "overall_status": "REVIEW REQUIRED",
            "visual_status": "REVIEW REQUIRED",
            "photos_reviewed": 2,
            "possible_issues": 0,
            "observations": 0,
            "actions": 0,
            "verify_items": 0,
        },
        "executive_summary": "Two photos reviewed.",
        "photo_register": [
            {
                "photo_ref": "P01",
                "category": "AV_EQUIPMENT",
                "subject_equipment": "Wall-mounted Crestron room scheduling touch panel.",
                "notes": "Crestron touch panel powered on.",
            },
            {
                "photo_ref": "P02",
                "category": "AV_EQUIPMENT",
                "subject_equipment": "AV equipment rack with rack-mounted devices.",
                "notes": "Rack and power distribution equipment visible.",
            },
        ],
        "visual_findings": [],
        "verification_items": [],
    }

    merged = merge_site_inspection_into_survey_data(base, summary)
    items = merged["inspection_sections"][0]["items"]
    assert "P01" in items[0]["photo_ref"]
    assert "P02" in items[1]["photo_ref"]



def test_client_facing_verify_suppresses_generic_not_visible_items():
    items = [
        {
            "file_name": "rack.jpg",
            "analysis": {
                "category": "AV_EQUIPMENT",
                "summary": "AV rack visible.",
                "visible_text": [],
                "devices": [],
                "observations": ["Rack equipment is visible."],
                "possible_issues": [],
                "uncertainties": [
                    "Rear cabling and connections behind the devices are not visible; connectivity cannot be confirmed.",
                    "The function of the top-right black box is not labeled and cannot be identified.",
                ],
            },
        }
    ]
    summary = build_site_inspection_summary(items)
    assert summary["verification_items"] == []
    assert summary["inspection_meta"]["verify_items"] == 0


def test_uncertainty_that_duplicates_visual_finding_is_not_repeated():
    items = [
        {
            "file_name": "ceiling.jpg",
            "analysis": {
                "category": "SITE_PHOTO",
                "summary": "Ceiling area visible.",
                "visible_text": [],
                "devices": [],
                "observations": ["A hanging cable is visible."],
                "possible_issues": [
                    {
                        "issue": "A loose cable appears to hang from the ceiling.",
                        "confidence": "medium",
                        "basis": "The cable is visibly unsupported near the ceiling fixture.",
                    }
                ],
                "uncertainties": [
                    "Whether the hanging cable is intended support or an unsecured cable requires site verification."
                ],
            },
        }
    ]
    summary = build_site_inspection_summary(items)
    assert len(summary["visual_findings"]) == 1
    assert summary["verification_items"] == []


def test_photo_linking_does_not_use_generic_poly_rack_for_tc10_or_g62():
    base = {
        "project_info": {"project_name": "Mastercard Riyadh"},
        "inspection_sections": [
            {
                "section_title": "Existing equipment to retain / reuse",
                "items": [
                    {
                        "inspection_item": "Verify retained 10” controller (Poly TC10 touch panel)",
                        "status": "VERIFY",
                    }
                ],
            },
            {
                "section_title": "New equipment / installation verification",
                "items": [
                    {
                        "inspection_item": "Verify installation feasibility for 1 x Poly Studio G62 codec",
                        "status": "VERIFY",
                    }
                ],
            },
        ],
    }
    summary = {
        "inspection_meta": {
            "overall_status": "REVIEW REQUIRED",
            "visual_status": "REVIEW REQUIRED",
            "photos_reviewed": 1,
            "possible_issues": 0,
            "observations": 0,
            "actions": 0,
            "verify_items": 0,
        },
        "executive_summary": "One photo reviewed.",
        "photo_register": [
            {
                "photo_ref": "P05",
                "category": "AV_EQUIPMENT",
                "subject_equipment": "AV rack with a Poly-branded VTC device and multiple rack units.",
                "notes": "Poly logo and VTC-01 asset tag are visible.",
            }
        ],
        "visual_findings": [],
        "verification_items": [],
    }

    merged = merge_site_inspection_into_survey_data(base, summary)
    assert merged["inspection_sections"][0]["items"][0].get("photo_ref", "") == ""
    assert merged["inspection_sections"][1]["items"][0].get("photo_ref", "") == ""


def test_merge_builds_deviation_action_rows_from_visual_observations():
    base = {
        "project_info": {"project_name": "Project X"},
        "inspection_sections": [],
    }
    summary = {
        "inspection_meta": {
            "overall_status": "REVIEW REQUIRED",
            "visual_status": "REVIEW REQUIRED",
            "photos_reviewed": 1,
            "possible_issues": 1,
            "observations": 1,
            "actions": 0,
            "verify_items": 0,
        },
        "executive_summary": "One photo reviewed.",
        "photo_register": [],
        "visual_findings": [
            {
                "id": "F-01",
                "source_photo_ref": "P01",
                "finding": "A loose cable is visible.",
                "confidence": "MEDIUM",
                "priority": "MEDIUM",
                "status": "OBSERVATION",
                "required_action": "Verify the condition on site.",
            }
        ],
        "verification_items": [],
    }

    merged = merge_site_inspection_into_survey_data(base, summary)
    rows = merged["deviations_risks_actions"]
    assert len(rows) == 1
    assert rows[0]["id"] == "F-01"
    assert rows[0]["photo_ref"] == "P01"
    assert rows[0]["priority"] == "MEDIUM"



def test_mastercard_style_generic_uncertainties_do_not_reach_client_verify_table():
    items = [
        {
            "file_name": "p01.jpg",
            "analysis": {
                "category": "SITE_PHOTO",
                "summary": "Boardroom visible.",
                "visible_text": [],
                "devices": [],
                "observations": ["A hanging cable is visible."],
                "possible_issues": [
                    {
                        "issue": "A loose or unsecured wire/cable appears to hang from the ceiling.",
                        "confidence": "medium",
                        "basis": "The cable is visibly unsupported near the ceiling fixture.",
                    }
                ],
                "uncertainties": [
                    "Whether the hanging wire is an intended suspension cable or a loose/unsecured conductor requires site verification.",
                    "Ceiling speaker brand, count, and wiring are not visible.",
                ],
            },
        },
        {
            "file_name": "p02.jpg",
            "analysis": {
                "category": "SITE_PHOTO",
                "summary": "Adjacent room visible.",
                "visible_text": [],
                "devices": [],
                "observations": ["Room area is visible."],
                "possible_issues": [],
                "uncertainties": [
                    "No AV/UC equipment is visible; devices may be out of frame or not yet installed.",
                    "Cable routing, power/data connections, and in-ceiling equipment cannot be assessed from this view.",
                ],
            },
        },
        {
            "file_name": "p03.jpg",
            "analysis": {
                "category": "SITE_PHOTO",
                "summary": "Crestron scheduling panel visible.",
                "visible_text": [],
                "devices": [],
                "observations": ["Scheduling panel is visible."],
                "possible_issues": [],
                "uncertainties": [
                    "Cable routing and connections behind the panel and wall are not visible and cannot be verified.",
                    "The brand/model of the background large display is not legible.",
                ],
            },
        },
        {
            "file_name": "p04.jpg",
            "analysis": {
                "category": "SITE_PHOTO",
                "summary": "Ceiling plenum visible.",
                "visible_text": [],
                "devices": [],
                "observations": ["Ceiling plenum is visible."],
                "possible_issues": [],
                "uncertainties": [
                    "The white label text on the small box is not legible; device identity is unknown.",
                    "Whether any hanging cables are terminated/connected to equipment is not visible.",
                ],
            },
        },
        {
            "file_name": "p05.jpg",
            "analysis": {
                "category": "AV_EQUIPMENT",
                "summary": "AV rack visible.",
                "visible_text": [],
                "devices": [],
                "observations": ["Rack equipment is visible."],
                "possible_issues": [],
                "uncertainties": [
                    "Rear cabling and connections behind the devices are not visible; connectivity cannot be confirmed.",
                    "The function of the top-right black box is not labeled and cannot be identified.",
                ],
            },
        },
    ]

    summary = build_site_inspection_summary(items)
    assert summary["inspection_meta"]["verify_items"] == 0
    assert summary["verification_items"] == []
