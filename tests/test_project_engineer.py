from datetime import date

from project_engineer import (
    PROJECT_PHASES,
    build_progress_report,
    build_project_drawing_register,
    classify_sheet_type,
    detect_report_period,
    format_progress_report_markdown,
    is_project_engineer_question,
    is_project_update_message,
    select_relevant_drawing_page_numbers,
)


def sample_pages():
    return [
        {
            "page_number": 1,
            "source": "Pinsent.pdf",
            "text": """
            PINSENT MASONS - RIYADH
            RIYADH KSA
            390I-25-88927
            AV-100 COVER SHEET
            AV-101 AUDIOVISUAL RESPONSIBILITY SCHEDULE & ABBREVIATIONS
            AV-201 FLOOR PLAN AV LAYOUT - 7 PAX MEETING ROOM (INTERNAL & EXTERNAL)
            AV-208 FLOOR PLAN AV DEVICE LAYOUT - DIVISIBLE MEETING ROOM
            AV-305 AV SIGNAL FLOW DIAGRAM - DIVISIBLE MEETING ROOM (SHEET 1 of 2)
            """,
        },
        {
            "page_number": 2,
            "source": "Pinsent.pdf",
            "text": """
            AV-101 AUDIOVISUAL SYSTEMS RESPONSIBILITY SCHEDULE & ABBREVIATIONS
            ALL REQUIRED BACKING AND ANY OTHER WALL REINFORCEMENT REQUIRED TO SAFELY ACCOMMODATE DISPLAYS.
            ALL AC POWER AT THE EQUIPMENT LOCATIONS.
            ALL REQUIRED CONDUIT FOR LOW VOLTAGE CABLE PATHS TO AV EQUIPMENT.
            ALL REQUIRED NETWORK CONFIGURATION FOR ANY NETWORK CONNECTION TO THE CLIENT NETWORK.
            ALL ROUGH WIRE PULLS SHALL BE PROPERLY LABELED AND TESTED WHEN TERMINATED.
            ANY SITE CHANGE NEED TO BE REDLINED AND RETURNED TO THE ENGINEERING TEAM FOR AS-BUILT DOCUMENTATION.
            VIF
            """,
        },
        {
            "page_number": 6,
            "source": "Pinsent.pdf",
            "text": """
            AV-200 AV SCOPE KEY PLAN
            L7-07 CLIENT MEETING 03
            L7-15 MEETING ROOM
            INTERNAL 7 PAX MEETING ROOM
            EXTERNAL 5 PAX MEETING ROOM
            DIVISIBLE MEETING ROOM
            """,
        },
        {
            "page_number": 7,
            "source": "Pinsent.pdf",
            "text": """
            AV-201 7 PAX MEETING ROOM (INTERNAL & EXTERNAL)
            FLOOR PLAN AV LAYOUT
            FLOOR PLAN AV CONTAINMENT LAYOUT
            AV DEVICE ELEVATION
            AV DEVICE SIGHTLINE
            """,
        },
        {
            "page_number": 20,
            "source": "Pinsent.pdf",
            "text": """
            AV-305 AV SIGNAL FLOW DIAGRAM - DIVISIBLE MEETING ROOM (SHEET 1 of 2)
            """,
        },
    ]


def test_classify_sheet_type():
    assert classify_sheet_type("AV SIGNAL FLOW DIAGRAM") == "signal_flow"
    assert classify_sheet_type("FLOOR PLAN AV CONTAINMENT LAYOUT") == "containment"
    assert classify_sheet_type("CEILING PLAN AV DEVICE LAYOUT") == "ceiling_plan"


def test_register_uses_full_drawing_set():
    register = build_project_drawing_register(sample_pages())

    assert register["project"]["project_name"] == "Pinsent Masons - Riyadh"
    assert register["project"]["location"] == "Riyadh, KSA"
    assert register["project"]["opportunity_number"] == "390I-25-88927"
    assert register["sheet_count"] == 5
    assert any("L7-07 CLIENT MEETING 03" in room for room in register["rooms"])
    assert "Divisible Meeting Room" in register["rooms"]
    assert any(
        item["category"] == "Network configuration"
        for item in register["coordination_requirements"]
    )
    assert any(item["type"] == "VIF" for item in register["risk_flags"])
    assert len(register["lifecycle_plan"]) == len(PROJECT_PHASES)
    assert register["lifecycle_plan"][1]["phase"] == "First Fix"


def test_project_update_detection():
    assert is_project_update_message("Today we completed cable pulling in Meeting Room 1.")
    assert is_project_update_message("اليوم خلصنا سحب الكيبلات وباقي البرمجة")
    assert not is_project_update_message("What is Dante?")


def test_daily_weekly_monthly_reports():
    logs = [
        {
            "date": "2026-09-21",
            "phase": "First Fix",
            "rooms": ["Room A"],
            "completed": ["Containment checked"],
            "issues": [],
            "blockers": [],
            "next_actions": ["Pull cables"],
        },
        {
            "date": "2026-09-22",
            "phase": "First Fix",
            "rooms": ["Room A", "Room B"],
            "completed": ["Cables pulled"],
            "issues": ["Missing data outlet"],
            "blockers": ["IT outlet pending"],
            "next_actions": ["Terminate cables"],
        },
    ]

    daily = build_progress_report(
        logs,
        period="daily",
        anchor_date=date(2026, 9, 22),
        project={"project_name": "Pinsent Masons - Riyadh"},
    )
    assert daily["entries_count"] == 1
    assert "Cables pulled" in daily["completed"]

    weekly = build_progress_report(
        logs,
        period="weekly",
        anchor_date=date(2026, 9, 22),
    )
    assert weekly["entries_count"] == 2
    assert "Missing data outlet" in weekly["issues"]

    monthly = build_progress_report(
        logs,
        period="monthly",
        anchor_date=date(2026, 9, 22),
    )
    assert monthly["entries_count"] == 2

    markdown = format_progress_report_markdown(monthly)
    assert "Monthly Project Report" in markdown
    assert "Missing data outlet" in markdown



def test_project_engineer_intents_and_page_selection():
    assert detect_report_period("اعمل تقرير أسبوعي") == "weekly"
    assert detect_report_period("monthly report please") == "monthly"
    assert is_project_engineer_question("شو ابلش بال first fix؟")

    pages = sample_pages()
    selected = select_relevant_drawing_page_numbers(
        pages,
        "Show me the divisible meeting room signal flow",
        max_pages=1,
    )
    assert selected == [20]
