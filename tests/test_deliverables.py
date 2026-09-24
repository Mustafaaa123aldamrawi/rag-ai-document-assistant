from io import BytesIO

from docx import Document

from deliverables import build_site_survey_report_docx


def sample_data():
    return {
        "project_info": {
            "project_name": "Mastercard Riyadh",
            "client": "Mastercard",
            "location": "Riyadh",
        },
        "rooms_areas": ["Room-1", "Room-2"],
        "checklist_sections": [
            {
                "section": "AV Rack",
                "items": [
                    {
                        "item": "Verify rack capacity",
                        "status": "VERIFY",
                        "notes": "",
                    },
                    {
                        "item": "Existing PDU retained",
                        "status": "PASS",
                        "notes": "Visible in scope.",
                    },
                ],
            }
        ],
        "required_photos": ["Rack front", "Rack rear"],
        "open_items": ["Confirm VLAN requirements"],
    }


def test_report_docx_is_valid_word_file():
    output = build_site_survey_report_docx(sample_data())
    assert output
    assert output[:2] == b"PK"


def test_report_contains_professional_sections():
    output = build_site_survey_report_docx(sample_data())
    document = Document(BytesIO(output))
    text = "\n".join(p.text for p in document.paragraphs)
    assert "AV SITE SURVEY REPORT" in text
    assert "Executive Summary" in text
    assert "Recommendations / Next Actions" in text
    assert "Draft / Pre-Survey Report" in text
